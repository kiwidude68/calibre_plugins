from __future__ import unicode_literals, division, absolute_import, print_function

__license__   = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import posixpath, os
from six.moves.urllib.parse import unquote

from calibre import fit_image
from calibre.utils.magick.draw import Image

class CoverUpdater(object):
    '''
    Class encapsulating all logic concerning identifying the cover in
    an ePub and replacing that if found, otherwise inserting a new cover
    '''
    def __init__(self, log, container, cover_path, opts):
        self.log = log
        self.container = container
        self.cover_path = cover_path
        self.opts = opts
        self.potential_unused_image_names = []
        self.toc_old_cover_content_node = None
        self.removed_html_name = None

    def remove_existing_cover(self):
        # Get manifest item for current cover in ePub if found, and remove
        # all guide/meta entries from the opf manifest
        existing_cover_item = self._get_and_clean_existing_cover_item()

        if existing_cover_item is not None:
            # If existing cover page contains only an image remove it completely
            self._remove_old_cover_if_safe(existing_cover_item)

        if self.removed_html_name is not None:
            # Is there a NCX TOC entry that needs removing?
            if self.toc_old_cover_content_node is not None:
                self.container.delete_from_toc(item_name=self.removed_html_name)
            # Is there an internal TOC entry that needs removing?
            self._update_html_links_to_old_cover(self.removed_html_name, None)

        # Cleanup any orphaned images
        self.log('\t...Remove any orphaned guide images')
        self.container.remove_unused_images(self.potential_unused_image_names)

        self.log('\t...Cover modifications completed')

    def insert_or_replace_cover(self):
        # Try to identify what subfolders the images and text files are stored
        # in so that we can write the replacement cover/image in same.
        self._identify_image_text_folders()

        # Get manifest item for current cover in ePub if found, and remove
        # all guide/meta entries from the opf manifest
        existing_cover_item = self._get_and_clean_existing_cover_item()

        if existing_cover_item is not None:
            # If existing cover page contains only an image remove it completely
            self._remove_old_cover_if_safe(existing_cover_item)

        # Generate a new titlepage containing our cover image
        titlepage_path, cover_path = self._create_new_cover(self.cover_path)

        # Add to the meta/manifest/spine/guide and update TOC if needed
        new_title_name = self._add_new_cover_to_manifest(titlepage_path, cover_path)

        # Ensure any html pages linking to old cover page have links updated
        if self.removed_html_name and self.removed_html_name != new_title_name:
            self._update_html_links_to_old_cover(self.removed_html_name, new_title_name)

        # Cleanup any orphaned images
        self.log('\t...Remove any orphaned guide images')
        self.container.remove_unused_images(self.potential_unused_image_names)

        # Apply any "fixes" to the manifest for device workarounds
        self.log('\t...Apply device specific fixes')
        self._ensure_opf_contains_cover_fixes()
        self.log('\t...Cover modifications completed')

    def _identify_image_text_folders(self):
        '''
        If the ePub has subfolders for the html and image pages identify what
        those are to ensure we can write replacement html/images into them
        '''
        self.images_folder = ''
        for image_name in self.container.get_image_names():
            if '/' in image_name:
                self.images_folder = os.path.dirname(image_name)
                break
        self.text_folder = ''
        for html_name in self.container.get_html_names():
            if '/' in html_name:
                self.text_folder = os.path.dirname(html_name)
                break

    def _get_and_clean_existing_cover_item(self):
        '''
        Look for whatever guide entry exists for a cover, and return the manifest
        item for it as well as removing existing guide and metadata entries
        from the opf file and noting any TOC reference pointing to it.
        '''
        # Look for ideal scenario of a guide reference of type 'cover'
        cover_item = self._get_guide_cover_item()
        # Remove from the meta tags if a cover has been defined that way
        metadata_cover_image_item = self._get_and_clean_meta_cover()
        if cover_item is None:
            cover_item = metadata_cover_image_item
        # Clean up any other guide cover references, picking best cover choice if any
        other_guide_cover_image_item = self._clean_other_guide_cover_references()
        if cover_item is None:
            cover_item = other_guide_cover_image_item

        if cover_item is not None:
            # Remove it from the guide as we will re-insert after new cover generated
            self.log('\t...Working with possible existing cover:', cover_item.get('href'))
            self.container.delete_from_guide(cover_item)

            # We have identified a cover 'item', want to cleanup references to it.
            # However at this point it could be that our 'item' is just the image,
            # and not the html page that is responsible for displaying it.
            mt = cover_item.get('media-type').lower()
            if mt.startswith('image/'):
                # We have a non-ideal ePub which only has a cover identified by image
                # Try to figure out first html page this image is linked to from
                self.log('\t...Looking for cover html page since identified cover is an image')
                cover_item = self._find_item_for_cover_image(cover_item)
                if cover_item is None:
                    # We haven't been able to find it, so will give up at this point
                    # and treat this as a scenario needing a new cover inserted.
                    self.log('\t  Aborting cover identification since no page found')
                    return None
                else:
                    self.log('\t  Switching to use this for cover page:', cover_item.get('href'))

            # Get any TOC reference to this cover choice, so we can update it later
            self.log('\t...Looking for TOC navpoint for this cover')
            self.toc_old_cover_content_node = self.container.get_toc_navpoint_content(cover_item)
            if self.toc_old_cover_content_node is not None:
                self.log('\t  Found navpoint to update')

            return cover_item

    def _get_guide_cover_item(self):
        '''
        Look for a guide reference of type 'cover' and if found return the
        manifest item for it.
        '''
        self.log('\t...Looking for guide cover reference')
        guide_cover = self.container.get_guide_reference(ref_type='cover')
        if guide_cover is not None:
            href = guide_cover.get('href').partition('#')[0]
            self.log('\t  Found guide cover reference to: ', href)
            guide_cover_name = self.container.href_to_name(href)
            guide_cover_item = self.container.get_manifest_item_for_name(guide_cover_name)
            if guide_cover_item is None:
                self.log('\t  Error in ePub: guide item does not exist in manifest')
            else:
                self.log('\t  Related manifest item id:', guide_cover_item.get('id'))
            return guide_cover_item

    def _get_and_clean_meta_cover(self):
        '''
        Look for a <meta name="cover" content="xxx" /> tag and if found
        delete it and return the manifest item it points to.

        Note that this will only find us at best an image, not the cover
        html page that image is on at this point.
        '''
        self.log('\t...Looking for meta cover')
        meta_item = self.container.get_meta_content_item('cover')
        if meta_item is not None:
            cover_id = meta_item.get('content')
            self.log('\t  Found meta tag with cover id:', cover_id)
            self.container.delete_from_metadata(meta_item)
            # Lookup the manifest item to return it
            meta_cover_item = self.container.get_manifest_item_by_id(cover_id)
            return meta_cover_item

    def _clean_other_guide_cover_references(self):
        '''
        Some ePubs rather than having a guide reference of type 'cover'
        will have one or more images of type 'other.ms-xxx' and have the
        first spine item pointing to an html cover page.

        If doing a conversion calibre will strip these, I will do the same.
        We need to pick one to assume it is the default cover image for the
        ePub based on its size to have any chance of removing its associated
        html page, since we have no way otherwise of guessing a cover page.

        Note that this will only find us at best an image, not the cover
        html page that image is on at this point.
        '''
        self.log('\t...Looking for other.ms-* guide references to clean out')
        covers = []
        for x in ('coverimagestandard', 'other.ms-coverimage-standard',
                'other.ms-titleimage-standard', 'other.ms-titleimage',
                'other.ms-coverimage', 'other.ms-thumbimage-standard',
                'other.ms-thumbimage', 'thumbimagestandard'):
            reference = self.container.get_guide_reference(ref_type=x)
            if reference is not None:
                href = reference.get('href')
                # Convert our href into a 'name' (rel path from epub root)
                image_name = self.container.href_to_name(href)
                if image_name not in self.container.raw_data_map:
                    # We have an invalid guide reference - is this a casing issue?
                    fixed = False
                    for name in self.container.raw_data_map.keys():
                        if name.lower() == image_name.lower():
                            self.log('\t  Fixing invalid cased href of: %s'%href)
                            image_name = name
                            href = self.container.name_to_href(image_name)
                            reference.set('href', href)
                            fixed = True
                    if not fixed:
                        self.log('\t  Invalid href to non-existent item: %s'%href)
                        continue

                # Add to our list to sort by size of cover
                image_data = self.container.get_raw(image_name)
                covers.append([reference, len(image_data)])
                # Add to our list of possible unused images to remove
                self.potential_unused_image_names.append(image_name)
                # Remove the guide reference as a best practice from Kovid
                self.container.delete_from_guide(reference)

        # Sort by the largest size
        covers.sort(key=lambda x:x[1], reverse=True)
        if covers:
            reference = covers[0][0]
            href = reference.get('href')
            self.log('\t  Choosing %s:%s as the cover: '%(href, reference.get('type')))
            # Note that it isn't the guide reference we want to return at this point,
            # but instead the manifest item that points to it.
            guide_name = self.container.href_to_name(href)
            guide_item = self.container.get_manifest_item_for_name(guide_name)
            return guide_item

    def _find_item_for_cover_image(self, image_item):
        '''
        For use when we don't yet know which html page an image which has been
        marked as being the cover is linked from on.
        Return manifest item for the html page if found.
        '''
        # Get our image name to lookup.
        cover_image_name = self.container.href_to_name(image_item.get('href')).lower()

        # Iterate through the spine (it's likely the first or last if any!)
        for manifest_item in self.container.get_spine_items():
            html_name = self.container.href_to_name(manifest_item.get('href'))
            for image_name, _orig_href, _node in self.container.get_page_image_names(html_name):
                if image_name.lower() == cover_image_name:
                    self.log('\t  Found this cover page:', html_name)
                    return manifest_item

    def _remove_old_cover_if_safe(self, cover_item):
        '''
        Remove the html page for the existing cover if that is all it contains.
        Otherwise remove the image from it, completely if not used elsewhere.
        '''
        html_name = self.container.href_to_name(cover_item.get('href'))
        image_name, _orig_href, image_node = None, None, None
        self.removed_html_name = ''

        self.log('\t...Inspecting old cover for removal')
        data = self.container.get_parsed_etree(html_name)
        image_links = list(self.container.get_page_image_names(html_name, data))
        if image_links:
            # Going to assume that the first image on this page is the cover
            image_name, _orig_href, image_node = image_links[0]
            image_node.getparent().remove(image_node)

        body_text = self.container.get_body_text(html_name)
        if not body_text and len(image_links) <= 1:
            # There is no text in this page and at most one svg and/or img links
            # Remove from manifest, guide, spine. Do not delete from TOC if exists
            # as we are going to re-point that entry to our new cover page
            self.log('\t  Cover page contains only this image so can be deleted')
            self.container.delete_from_manifest(html_name, delete_from_toc=False)
            # Store the removed html page name so we can later look for html
            # pages that referred to this cover page (like an inline TOC).
            self.removed_html_name = html_name
        else:
            # The page contains either other text or other images
            # We've removed the first image so write the page data back
            self.log('\t  Cover image link removed, page kept but no longer will be cover')
            self.container.set(html_name, data)

        if image_name is not None:
            # Was the cover image only used on this page? If so, remove it now.
            self.log('\t  Checking safe to remove cover image:', image_name)
            cover_image_item = self.container.get_manifest_item_for_name(image_name)
            if cover_image_item is not None:
                referenced_html_item = self._find_item_for_cover_image(cover_image_item)
                if referenced_html_item is None:
                    # There are no html pages left referring to this cover
                    self.log('\t  No other html pages use this image, safe to remove')
                    self.container.delete_from_manifest(image_name)

    def _create_new_cover(self, existing_cover_path):
        '''
        Generate a calibre cover page using specified image.
        Returns path to html titlepage and image
        '''
        self.log('\t...Writing new cover image and titlepage html')

        # Begin by resizing our cover image if necessary for configured device
        with open(existing_cover_path, 'rb') as f:
            cover_data = f.read()
        cover_data, width, height = self._rescale_cover(cover_data)
        # Save to a safe filename in the root of the epub folder
        cname = 'cover.jpeg'
        if self.images_folder:
            cname = self.images_folder + '/' + cname
        cover_path = self._get_unique_filename(cname)
        with open(cover_path, 'wb') as f:
            f.write(cover_data)
        cover_name = os.path.relpath(cover_path, self.container.root).replace(os.sep, '/')
        self.log('\t  New cover image written to: %s'%cover_name)

        # Generate our new titlepage.
        titlepage_name = self._create_titlepage(cover_name, width, height)
        self.log('\t  New titlepage html written to: %s'%titlepage_name)

        return titlepage_name, cover_name

    def _get_unique_filename(self, preferred_name):
        base_dir = self.container.root
        fname = os.path.normpath(posixpath.join(base_dir, preferred_name))
        base, ext = posixpath.splitext(fname)
        c = 0
        while True:
            if not posixpath.exists(fname):
                return fname
            c += 1
            suffix = '_u%d'%c
            fname = base + suffix + ext

    def _create_titlepage(self, cover_href, width, height):
        from calibre.ebooks.oeb.transforms.cover import CoverManager

        tname = 'titlepage.xhtml'
        if self.text_folder:
            tname = self.text_folder + '/' + tname
        titlepage_path = self._get_unique_filename(tname)

        # Prepare template based on users default options
        if width is None or height is None:
            self.log.warning('Failed to read cover dimensions')
            width, height = 600, 800
        if self.opts.no_svg_cover:
            style = 'style="height: 100%%"'
            templ = CoverManager.NONSVG_TEMPLATE.replace('__style__', style)
        else:
            ar = 'xMidYMid meet' if self.opts.preserve_cover_aspect_ratio else 'none'
            templ = CoverManager.SVG_TEMPLATE.replace('__ar__', ar)
            templ = templ.replace('__viewbox__', '0 0 %d %d'%(width, height))
            templ = templ.replace('__width__',  str(width))
            templ = templ.replace('__height__', str(height))

        rel_path = os.path.relpath(cover_href, os.path.dirname(tname))
        rel_cover_href = os.path.normpath(rel_path).replace('\\','/')
        tp = templ%unquote(rel_cover_href)

        with open(titlepage_path, 'w') as f:
            f.write(tp)
        titlepage_name = os.path.relpath(titlepage_path, self.container.root).replace(os.sep, '/')
        return titlepage_name

    def _rescale_cover(self, raw):
        try:
            img = Image()
            img.load(raw)
        except:
            self.log.exception('Exception while trying to resize image')
            return raw, None, None

        width, height = img.size
        page_width, page_height = self.opts.dest.width, self.opts.dest.height
        page_width -= (self.opts.margin_left + self.opts.margin_right) * self.opts.dest.dpi/72.
        page_height -= (self.opts.margin_top + self.opts.margin_bottom) * self.opts.dest.dpi/72.
        scaled, new_width, new_height = fit_image(width, height,
                page_width, page_height)
        if scaled:
            new_width = max(1, new_width)
            new_height = max(1, new_height)
            self.log('\t  Rescaling cover image from %dx%d to %dx%d'%(
                width, height, new_width, new_height))
            try:
                img.size = (new_width, new_height)
                data = img.export('jpeg')
            except:
                self.log.exception('Failed to rescale image')
            else:
                raw = data
        return raw, new_width, new_height


    def _add_new_cover_to_manifest(self, titlepage_name, cover_name):
        '''
        Perform all the necessary steps to get our new titlepage and cover image
        listed in the opf manifest and updated reference by TOC if necessary
        '''
        self.log('\t...Updating manifest and TOC for the new cover')

        # Add a titlepage entry into the manifest items
        titlepage_href = self.container.name_to_href(titlepage_name)
        titlepage_id, titlepage_href = self.container.generate_unique(id='titlepage', href=titlepage_href)
        self.container.add_to_manifest(titlepage_id, titlepage_href)

        # Add a cover image entry into the manifest items
        cover_href = self.container.name_to_href(cover_name)
        cover_id, cover_href = self.container.generate_unique(id='cover', href=cover_href)
        self.container.add_to_manifest(cover_id, cover_href)

        # Add a <meta> tag
        self.container.add_to_metadata('cover', cover_id)

        # Insert as first item in spine
        self.container.add_to_spine(titlepage_id, 0)

        # Add guide reference entry
        self.container.add_to_guide(titlepage_href, 'Cover', 'cover')

        # Re-point the TOC NCX entry if needed
        if self.toc_old_cover_content_node is not None:
            titlepage_name = self.container.href_to_name(titlepage_href)
            rel_path = os.path.relpath(titlepage_name, os.path.dirname(self.container.ncx_name))
            new_href = os.path.normpath(rel_path).replace('\\','/')
            self.log('\t  Setting TOC entry to new href: ', new_href)
            self.toc_old_cover_content_node.set('src', new_href)
            self.container.set(self.container.ncx_name, self.container.ncx)

        # Return the name of the new titlepage relative to the root of the epub
        return self.container.href_to_name(titlepage_href)


    def _update_html_links_to_old_cover(self, removed_html_name, new_title_name):
        '''
        We have removed the old html page from this ePub. It might however have
        been linked to from an internal TOC in which case we need to write new links.
        '''
        self.log('\t...Looking for inline links to removed cover page:', removed_html_name)
        for html_name in self.container.get_html_names():
            data = self.container.get_parsed_etree(html_name)
            for href_name, href, node in self.container.get_page_href_names(html_name, data):
                if href_name.lower() == removed_html_name.lower():
                    if new_title_name is not None:
                        # We have a new cover page to link to
                        rel_path = os.path.relpath(new_title_name, os.path.dirname(html_name))
                        new_href = os.path.normpath(rel_path).replace('\\','/')
                        self.log('\t  Replacing internal TOC cover link from:', href, 'to:', new_href, 'in:', html_name)
                        node.set('href', new_href)
                    else:
                        # We have no cover page, so remove the link.
                        node.getparent().remove(node)
                        self.log('\t  Removing internal TOC cover link of:', href, 'in:', html_name)
                    self.container.set(html_name, data)

    def _ensure_opf_contains_cover_fixes(self):
        '''
        These fixes ensure that the <meta> tag for the cover has a content
        of 'cover' and the corresponding manifest item of 'cover' is first item.
        '''
        root = self.container.opf
        from calibre.customize.ui import plugin_for_output_format
        oeb_output = plugin_for_output_format('oeb')
        oeb_output.log = self.log
        # First workaround ensures the cover id is set to 'cover'
        try:
            oeb_output.workaround_nook_cover_bug(root)
        except Exception as ex:
            self.log.exception('Something went wrong while trying to'
                    ' workaround Nook cover bug, ignoring')
            self.log.exception('ERROR: ', ex)

        # Second workaround ensures the manifest item for cover img is placed first
        # Inlining this fix because calibre code makes a mess of the formatting
        # of the opf file by not caring about the tail of removed items.
        try:
            item = self.container.get_manifest_item_by_id('cover')
            if item is not None:
                self.container.fix_tail_before_delete(item)
                p = item.getparent()
                p.remove(item)
                p.insert(0, item)
                self.container.fix_tail_after_insert(item)
        except Exception as ex:
            self.log.exception('Something went wrong while trying to'
                    ' workaround Pocketbook cover bug, ignoring')
            self.log.exception('ERROR: ', ex)

        # Warning - at this point our opf xml could differ from the
        self.container.set(self.container.opf_name, self.container.opf)
