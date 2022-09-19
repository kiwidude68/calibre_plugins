from __future__ import unicode_literals, division, absolute_import, print_function

__license__ = 'GPL v3'
__copyright__ = '2011, Grant Drake'

import os
import six
from calibre import fit_image, force_unicode
from calibre.ebooks import normalize
from calibre.ebooks.metadata import authors_to_string
from calibre.utils.magick import Image
from calibre.utils.magick.draw import create_canvas
from calibre.utils.imghdr import identify

import calibre_plugins.generate_cover.config as cfg


def get_image_size(image_path):
    fmt, width, height = identify(open(image_path, 'rb'))
    return width, height


def swap_author_names(author):
    if author == None:
        return author
    if author.find(',') == -1:
        return author
    name_parts = author.strip().partition(',')
    return name_parts[2].strip() + ' ' + name_parts[0]


class TextLine(object):

    def __init__(self, text, font_name, font_size,
                 bottom_margin=30, align='center'):
        self.text = force_unicode(text)
        self.bottom_margin = bottom_margin
        try:
            from qt.core import QFont, Qt
        except ImportError:
            from PyQt5.Qt import QFont, Qt
        self.font = QFont(font_name) if font_name else QFont()
        self.font.setPixelSize(font_size)
        self._align = {'center': Qt.AlignHCenter,
                       'left': Qt.AlignLeft, 'right': Qt.AlignRight}[align]


def get_textline(text, font_info, margin):
    return TextLine(text, font_info['name'], font_info['size'], margin,
                    align=font_info['align'])


class DrawingWand(object):

    def __init__(self, **kw):
        for k, v in six.iteritems(kw):
            setattr(self, k, v)


def create_colored_text_wand(line, fill_color, stroke_color):
    return DrawingWand(**{
        'fill_color': fill_color, 'stroke_color':
        stroke_color, 'font': line.font, 'align': line._align})


def add_border(img, border_width, border_color, bgcolor):
    lwidth, lheight = img.size
    bg_canvas = create_canvas(lwidth, lheight, bgcolor)
    border_canvas = create_canvas(
        lwidth + border_width * 2, lheight + border_width * 2, border_color)
    border_canvas.compose(bg_canvas, int(border_width), int(border_width))
    border_canvas.compose(img, int(border_width), int(border_width))
    return border_canvas


def draw_sized_text(img, dw, line, top, left_margin, right_margin,
                    auto_reduce_font):
    try:
        from qt.core import QPainter, Qt, QRect, QColor
    except ImportError:
        from PyQt5.Qt import QPainter, Qt, QRect, QColor
    total_margin = left_margin + right_margin
    if img.size[0] - total_margin <= 0:
        total_margin = 0
        left_margin = 0
        right_margin = 0
    p = QPainter(img.img)
    try:
        # qt6
        p.setRenderHint(p.RenderHint.TextAntialiasing)
    except:
        # qt5
        p.setRenderHint(p.TextAntialiasing)
    pen = p.pen()
    pen.setColor(QColor(dw.fill_color))
    p.setPen(pen)
    flags = line._align
    try:
        if auto_reduce_font:
            line_width = img.size[0] - total_margin
            initial_font_size = line.font.pixelSize()
            text = line.text
            while True:
                f = line.font
                p.setFont(f)
                br = p.boundingRect(
                    0, 0, line_width, 100, flags | Qt.TextSingleLine, text)
                if br.width() < line_width:
                    break
                oversize_factor = br.width() / line_width
                if oversize_factor > 10:
                    f.setPixelSize(f.pixelSize() - 8)
                elif oversize_factor > 5:
                    f.setPixelSize(f.pixelSize() - 4)
                elif oversize_factor > 3:
                    f.setPixelSize(f.pixelSize() - 2)
                else:
                    f.setPixelSize(f.pixelSize() - 1)
                if f.pixelSize() < 6:
                    # Enough is enough, clearly cannot fit on one line!
                    # Abort the font reduction process
                    f.setPixelSize(initial_font_size)
                    line.text = '*** TEXT TOO LARGE TO AUTO-FIT ***'
                    break
        p.setFont(line.font)
        br = p.drawText(QRect(
            left_margin, top, img.size[0] - left_margin - right_margin,
            img.size[1] - top), flags | Qt.TextWordWrap, line.text)
        return br.bottom()
    finally:
        p.end()


def scaleup_image(width, height, pwidth, pheight):
    '''
    Fit image in box of width pwidth and height pheight.
    @param width: Width of image
    @param height: Height of image
    @param pwidth: Width of box
    @param pheight: Height of box
    @return: scaled, new_width, new_height. scaled is True iff new_width and/or
            new_height is different from width or height.
    '''
    image_ratio = width / float(height)
    box_ratio = pwidth / float(pheight)
    if image_ratio > box_ratio:
        width, height = pwidth, pwidth / image_ratio
    else:
        width, height = pheight * image_ratio, pheight

    return True, int(width), int(height)


def create_cover_page(top_lines, bottom_lines, display_image, options,
                      image_path, output_format='jpg'):
    from calibre.gui2 import ensure_app
    ensure_app()
    (width, height) = options.get(cfg.KEY_SIZE, (590, 750))
    def size_limit(i):
        if i < 100:
            return 100
        if i > 5000:
            return 5000
        return i
    width = size_limit(width)
    height = size_limit(height)
    margins = options.get(cfg.KEY_MARGINS)
    (top_mgn, bottom_mgn, left_mgn, right_mgn, image_mgn) = (
        margins['top'], margins['bottom'], margins['left'],
        margins['right'], margins['image'])
    left_mgn = min([left_mgn, (width / 2) - 10])
    left_text_margin = left_mgn if left_mgn > 0 else 10
    right_mgn = min([right_mgn, (width / 2) - 10])
    right_text_margin = right_mgn if right_mgn > 0 else 10

    colors = options[cfg.KEY_COLORS]
    bgcolor, border_color, fill_color, stroke_color = (
        colors['background'], colors['border'], colors['fill'],
        colors['stroke'])
    if not options.get(cfg.KEY_COLOR_APPLY_STROKE, False):
        stroke_color = None
    auto_reduce_font = options.get(cfg.KEY_FONTS_AUTOREDUCED, False)
    borders = options[cfg.KEY_BORDERS]
    (cover_border_width, image_border_width) = (
        borders['coverBorder'], borders['imageBorder'])
    is_background_image = options.get(cfg.KEY_BACKGROUND_IMAGE, False)
    if image_path:
        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            display_image = is_background_image = False

    canvas = create_canvas(width - cover_border_width * 2,
                           height - cover_border_width * 2, bgcolor)
    if cover_border_width > 0:
        canvas = add_border(canvas, cover_border_width, border_color, bgcolor)

    if is_background_image:
        logo = Image()
        logo.open(image_path)
        outer_margin = 0 if cover_border_width == 0 else cover_border_width
        logo.size = (width - outer_margin * 2, height - outer_margin * 2)
        left = top = outer_margin
        canvas.compose(logo, int(left), int(top))

    top = top_mgn
    if len(top_lines) > 0:
        for line in top_lines:
            twand = create_colored_text_wand(line, fill_color, stroke_color)
            top = draw_sized_text(
                canvas, twand, line, top, left_text_margin,
                right_text_margin, auto_reduce_font)
            top += line.bottom_margin
        top -= top_lines[-1].bottom_margin

    if len(bottom_lines) > 0:
        # Draw this on a fake canvas so can determine the space required
        fake_canvas = create_canvas(width, height, bgcolor)
        footer_height = 0
        for line in bottom_lines:
            line.twand = create_colored_text_wand(
                line, fill_color, stroke_color)
            footer_height = draw_sized_text(
                fake_canvas, line.twand, line, footer_height, left_text_margin,
                right_text_margin, auto_reduce_font)
            footer_height += line.bottom_margin
        footer_height -= bottom_lines[-1].bottom_margin

        footer_top = height - footer_height - bottom_mgn
        bottom = footer_top
        # Re-use the text wand from previously which we will have adjusted the
        # font size on
        for line in bottom_lines:
            bottom = draw_sized_text(
                canvas, line.twand, line, bottom, left_text_margin,
                right_text_margin, auto_reduce_font=False)
            bottom += line.bottom_margin
        available = (width - (left_mgn + right_mgn),
                     int(footer_top - top) - (image_mgn * 2))
    else:
        available = (width - (left_mgn + right_mgn),
                     int(height - top) - bottom_mgn - (image_mgn * 2))

    if not is_background_image and display_image and available[1] > 40:
        logo = Image()
        logo.open(image_path)
        lwidth, lheight = logo.size
        available = (available[0] - image_border_width * 2,
                     available[1] - image_border_width * 2)
        scaled, lwidth, lheight = fit_image(lwidth, lheight, *available)
        if not scaled and options.get(cfg.KEY_RESIZE_IMAGE_TO_FIT, False):
            scaled, lwidth, lheight = scaleup_image(
                lwidth, lheight, *available)
        if scaled:
            logo.size = (lwidth, lheight)
        if image_border_width > 0:
            logo = add_border(logo, image_border_width, border_color, bgcolor)

        left = int(max(0, (width - lwidth) / 2.))
        top = top + image_mgn + ((available[1] - lheight) / 2.)
        canvas.compose(logo, int(left), int(top))

    return canvas.export(output_format)


def get_title_author_series(mi, options=None):
    if not options:
        options = cfg.plugin_prefs[cfg.STORE_CURRENT]
    title = normalize(mi.title)
    authors = mi.authors
    if options.get(cfg.KEY_SWAP_AUTHOR, False):
        swapped_authors = []
        for author in authors:
            swapped_authors.append(swap_author_names(author))
        authors = swapped_authors
    author_string = normalize(authors_to_string(authors))

    series = None
    if mi.series:
        series_text = options.get(cfg.KEY_SERIES_TEXT, '')
        if not series_text:
            series_text = cfg.DEFAULT_SERIES_TEXT
        from calibre.ebooks.metadata.book.formatter import SafeFormat
        series = SafeFormat().safe_format(
            series_text, mi, 'GC template error', mi)
    series_string = normalize(series)
    return (title, author_string, series_string)


def split_and_replace_newlines(text):
    text = text.replace('\\n', '<br/>').replace('<br>', '<br/>')
    return text.split('<br/>')


def generate_cover_for_book(mi, options=None, db=None):
    if not options:
        options = cfg.plugin_prefs[cfg.STORE_CURRENT]
    title, author_string, series_string = get_title_author_series(mi, options)
    custom_text = options.get(cfg.KEY_CUSTOM_TEXT, None)
    if custom_text:
        from calibre.ebooks.metadata.book.formatter import SafeFormat
        custom_text = SafeFormat().safe_format(
            custom_text.replace('\n', '<br/>'), mi, 'GC template error', mi)

    fonts = options[cfg.KEY_FONTS]
    margin = options[cfg.KEY_MARGINS]['text']
    content_lines = {}
    content_lines['Title'] = [
        get_textline(title_line.strip(), fonts['title'], margin)
        for title_line in split_and_replace_newlines(title)]
    content_lines['Author'] = [
        get_textline(author_line.strip(), fonts['author'], margin)
        for author_line in split_and_replace_newlines(author_string)]
    if series_string:
        content_lines['Series'] = [
            get_textline(series_line.strip(), fonts['series'], margin)
            for series_line in split_and_replace_newlines(series_string)]
    if custom_text:
        content_lines['Custom Text'] = [
            get_textline(ct.strip(), fonts['custom'], margin)
            for ct in split_and_replace_newlines(custom_text)]
    top_lines = []
    bottom_lines = []
    field_order = options[cfg.KEY_FIELD_ORDER]
    above_image = True
    display_image = False
    for field in field_order:
        field_name = field['name']
        if field_name == 'Image':
            display_image = field['display']
            above_image = False
            continue
        if field_name not in content_lines:
            continue
        if field['display']:
            lines = content_lines[field_name]
            for line in lines:
                if above_image:
                    top_lines.append(line)
                else:
                    bottom_lines.append(line)

    image_name = options[cfg.KEY_IMAGE_FILE]
    image_path = None
    if image_name == cfg.TOKEN_CURRENT_COVER:
        image_path = getattr(mi, '_path_to_cover', None)
        if not image_path and db:
            image_path = mi._path_to_cover = db.cover(mi.id, as_path=True)
    elif image_name == cfg.TOKEN_DEFAULT_COVER:
        image_path = I('library.png')  # noqa
    else:
        image_path = os.path.join(cfg.get_images_dir(), image_name)
    if image_path is None or not os.path.exists(image_path):
        image_path = I('library.png')  # noqa
    return create_cover_page(
        top_lines, bottom_lines, display_image, options, image_path)
