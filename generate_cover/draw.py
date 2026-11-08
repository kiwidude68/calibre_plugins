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
try:
    from qt.core import QFont, Qt, QPainter, Qt, QRect, QColor, QFontMetrics
    weight_map = {
        "Light": QFont.Weight.Light,
        "Normal": QFont.Weight.Normal,      # <--- Fixed here
        "Demi Bold": QFont.Weight.DemiBold,
        "Bold": QFont.Weight.Bold,
        "Black": QFont.Weight.Black,
    }
    default_font_weight = QFont.Weight.Normal
except ImportError:
    from PyQt5.Qt import QFont, Qt, QPainter, Qt, QRect, QColor, QFontMetrics
    weight_map = {
        "Light": QFont.Light,
        "Normal": QFont.Normal,      # <--- Fixed here
        "Demi Bold": QFont.DemiBold,
        "Bold": QFont.Bold,
        "Black": QFont.Black,
    }
    default_font_weight = QFont.Normal

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
                 bottom_margin=30, align='center', fill_color='#000000',
                 weight='Normal', italic=False, underline=False):
        self.text = force_unicode(text)
        self.bottom_margin = bottom_margin
        self.fill_color = fill_color
        self.font = QFont(font_name) if font_name else QFont()
        self.font.setPixelSize(font_size)

        self.font.setWeight(weight_map.get(weight, default_font_weight))
        self.font.setItalic(bool(italic))
        self.font.setUnderline(bool(underline))
        self._font_align = align
        self._align = {'center': Qt.AlignHCenter,
                       'left': Qt.AlignLeft, 'right': Qt.AlignRight}[align]
        self.backdrop_enabled = False
        self.backdrop_color = '#000000'
        self.backdrop_opacity = 70
        self.backdrop_padding = 4

    def apply_element_options(self, field):
        self.text_padding = field.get(
            cfg.KEY_FIELD_TEXT_PADDING,
            cfg.DEFAULT_ELEMENT_OPTIONS[cfg.KEY_FIELD_TEXT_PADDING])
        self.rotation = field.get(cfg.KEY_FIELD_ROTATION, 0)
        self.rotation_side = field.get(cfg.KEY_FIELD_ROTATION_SIDE, 'left')
        self.backdrop_enabled = field.get(cfg.KEY_FIELD_BACKDROP, False)
        self.backdrop_full_width = field.get(
            cfg.KEY_FIELD_BACKDROP_FULL_WIDTH, False)
        self.backdrop_color = field.get(cfg.KEY_FIELD_BACKDROP_COLOR, '#000000')
        self.backdrop_opacity = field.get(cfg.KEY_FIELD_BACKDROP_OPACITY, 70)
        self.backdrop_padding = field.get(
            cfg.KEY_FIELD_BACKDROP_PADDING,
            cfg.DEFAULT_ELEMENT_OPTIONS[cfg.KEY_FIELD_BACKDROP_PADDING])


def get_textline(text, font_info, margin, fill_color='#000000'):
    return TextLine(text, font_info['name'], font_info['size'], margin,
                    align=font_info['align'], fill_color=fill_color,
                    weight=font_info.get('weight', default_font_weight),
                    italic=font_info.get('italic', False),
                    underline=font_info.get('underline', False))


class DrawingWand(object):

    def __init__(self, **kw):
        for k, v in six.iteritems(kw):
            setattr(self, k, v)


def create_colored_text_wand(line):
    return DrawingWand(**{'fill_color': line.fill_color, 'stroke_color': None, 'font': line.font, 'align': line._align})


def backdrop_padding_for_rotation(padding, angle):
    if angle == 90:
        return {
            'left': padding['top'], 'right': padding['bottom'],
            'top': padding['right'], 'bottom': padding['left'],
        }
    if angle == 180:
        return {
            'left': padding['right'], 'right': padding['left'],
            'top': padding['bottom'], 'bottom': padding['top'],
        }
    if angle == 270:
        return {
            'left': padding['bottom'], 'right': padding['top'],
            'top': padding['left'], 'bottom': padding['right'],
        }
    return padding


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
    left_margin += line.text_padding['left']
    right_margin += line.text_padding['right']
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
        text_rect = QRect(
            int(left_margin), int(top), int(img.size[0] - left_margin - right_margin), int(img.size[1] - top))
        text_rect_y = text_rect.y()
        if line.rotation == 180:
            p.translate(text_rect.x() + text_rect.width(),
                        text_rect.y() + text_rect.height())
            p.rotate(180)
            text_rect = QRect(0, 0, text_rect.width(), text_rect.height())
        if line.backdrop_enabled:
            backdrop_rect = p.boundingRect(text_rect, flags | Qt.TextWordWrap, line.text)
            padding = backdrop_padding_for_rotation(
                line.backdrop_padding, line.rotation)
            if line.backdrop_full_width:
                backdrop_rect = QRect(
                    0, backdrop_rect.y(), int(img.size[0]), backdrop_rect.height())
                backdrop_rect.adjust(
                    0, -int(padding['top']), 0, int(padding['bottom']))
            else:
                backdrop_rect.adjust(
                    -int(padding['left']), -int(padding['top']),
                    int(padding['right']), int(padding['bottom']))
            backdrop_color = QColor(line.backdrop_color)
            if backdrop_color.isValid():
                backdrop_color.setAlpha(int(line.backdrop_opacity * 255 / 100))
                p.fillRect(backdrop_rect, backdrop_color)
        br = p.drawText(text_rect, flags | Qt.TextWordWrap, line.text)
        return text_rect_y + br.height() if line.rotation == 180 else br.bottom()
    finally:
        p.end()


def measure_text_height(img, line, left_margin, right_margin):
    left_margin += line.text_padding['left']
    right_margin += line.text_padding['right']
    if img.size[0] - left_margin - right_margin <= 0:
        left_margin = right_margin = 0
    text_width = max(1, img.size[0] - left_margin - right_margin)
    p = QPainter(img.img)
    try:
        p.setFont(line.font)
        bounds = p.boundingRect(
            QRect(0, 0, text_width, 100000),
            line._align | Qt.TextWordWrap, line.text)
        return bounds.height()
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


def prepare_rotated_field(lines, edge_length):
    padding = lines[0].text_padding
    backdrop_padding = (
        lines[0].backdrop_padding if lines[0].backdrop_enabled else
        dict.fromkeys(('top', 'bottom', 'left', 'right'), 0))
    vertical_backdrop_padding = (
        dict.fromkeys(('top', 'bottom'), 0)
        if lines[0].backdrop_full_width else backdrop_padding)
    local_backdrop_padding = (
        backdrop_padding_for_rotation(backdrop_padding, lines[0].rotation)
        if lines[0].backdrop_enabled and not lines[0].backdrop_full_width else
        dict.fromkeys(('top', 'bottom', 'left', 'right'), 0))
    available_length = max(
        1, edge_length - padding['top'] - padding['bottom'] -
        vertical_backdrop_padding['top'] - vertical_backdrop_padding['bottom'])
    text = '\n'.join(line.text for line in lines)
    font_metrics = QFontMetrics(lines[0].font)
    bounds = font_metrics.boundingRect(
        QRect(0, 0, available_length, 5000), Qt.TextWordWrap, text)
    text_width = max(1, min(available_length, bounds.width()))
    text_height = max(font_metrics.height(), bounds.height())
    return {
        'lines': lines,
        'angle': lines[0].rotation,
        'side': lines[0].rotation_side,
        'text': text,
        'text_width': text_width,
        'text_height': text_height,
        'rail_width': (
            text_height + padding['left'] + padding['right'] +
            backdrop_padding['left'] + backdrop_padding['right']),
        'padding': padding,
        'backdrop_padding': backdrop_padding,
        'local_backdrop_padding': local_backdrop_padding,
        'vertical_backdrop_padding': vertical_backdrop_padding,
    }


def draw_rotated_field(img, field, x, top, edge_length):
    lines = field['lines']
    angle = field['angle']
    padding = field['padding']
    backdrop_padding = field['backdrop_padding']
    local_backdrop_padding = field['local_backdrop_padding']
    vertical_backdrop_padding = field['vertical_backdrop_padding']
    text_width = field['text_width']
    text_height = field['text_height']
    available_length = max(
        1, edge_length - padding['top'] - padding['bottom'] -
        vertical_backdrop_padding['top'] - vertical_backdrop_padding['bottom'])
    align = lines[0]._font_align
    align_factor = {'left': 0, 'center': 0.5, 'right': 1}[align]
    aligned_offset = max(0, available_length - text_width) * align_factor
    text_top = (top + padding['top'] + vertical_backdrop_padding['top'] +
                aligned_offset)

    p = QPainter(img.img)
    try:
        try:
            p.setRenderHint(p.RenderHint.TextAntialiasing)
        except AttributeError:
            p.setRenderHint(p.TextAntialiasing)
        p.save()
        if lines[0].backdrop_enabled and lines[0].backdrop_full_width:
            full_backdrop_padding = lines[0].backdrop_padding
            backdrop_width = (
                text_height + int(full_backdrop_padding['left']) +
                int(full_backdrop_padding['right']))
            backdrop_left = x + padding['left']
            backdrop_rect = QRect(
                int(backdrop_left), 0, int(backdrop_width), int(img.size[1]))
            backdrop_color = QColor(lines[0].backdrop_color)
            if backdrop_color.isValid():
                backdrop_color.setAlpha(int(lines[0].backdrop_opacity * 255 / 100))
                p.fillRect(backdrop_rect, backdrop_color)
        if angle == 90:
            p.translate(
                x + padding['left'] + backdrop_padding['left'] + text_height,
                text_top)
            p.rotate(90)
        else:
            p.translate(
                x + padding['left'] + backdrop_padding['left'],
                text_top + text_width)
            p.rotate(270)

        text_rect = QRect(0, 0, int(text_width), int(text_height))
        if lines[0].backdrop_enabled and not lines[0].backdrop_full_width:
            backdrop_rect = QRect(text_rect)
            backdrop_rect.adjust(
                -int(local_backdrop_padding['left']),
                -int(local_backdrop_padding['top']),
                int(local_backdrop_padding['right']),
                int(local_backdrop_padding['bottom']))
            backdrop_color = QColor(lines[0].backdrop_color)
            if backdrop_color.isValid():
                backdrop_color.setAlpha(int(lines[0].backdrop_opacity * 255 / 100))
                p.fillRect(backdrop_rect, backdrop_color)
        p.setFont(lines[0].font)
        p.setPen(QColor(lines[0].fill_color))
        p.drawText(text_rect, Qt.TextWordWrap | Qt.AlignLeft | Qt.AlignTop, field['text'])
        p.restore()
    finally:
        p.end()


def create_cover_page(top_lines, bottom_lines, rotated_fields, display_image, options,
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
    (top_mgn, bottom_mgn, left_mgn, right_mgn) = (
        margins['top'], margins['bottom'], margins['left'],
        margins['right'])
    left_mgn = min([left_mgn, (width / 2) - 10])
    right_mgn = min([right_mgn, (width / 2) - 10])
    edge_length = max(1, height - top_mgn - bottom_mgn)
    
    rotated_fields = {
        side: [prepare_rotated_field(field, edge_length) for field in rotated_fields[side]]
        for side in ('left', 'right')
    }
    left_rail_width = sum(field['rail_width'] for field in rotated_fields['left'])
    right_rail_width = sum(field['rail_width'] for field in rotated_fields['right'])
    content_left_margin = left_mgn + left_rail_width
    content_right_margin = right_mgn + right_rail_width
    left_text_margin = content_left_margin if content_left_margin > 0 else 10
    right_text_margin = content_right_margin if content_right_margin > 0 else 10
    # image_padding should come from the image field in the field order, if present, otherwise use the default
    image_padding = {'top': 0, 'bottom': 0, 'left': 0, 'right': 0}
    for field in options[cfg.KEY_FIELD_ORDER]:
        if field['name'] == 'Image':
            image_padding = field.get(cfg.KEY_FIELD_IMAGE_PADDING, image_padding)
            break

    colors = options[cfg.KEY_COLORS]
    bgcolor, border_color = (
        colors['background'], colors['border'])
    image_border_color = colors.get(cfg.KEY_IMAGE_BORDER_COLOR, border_color)
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
        left = outer_margin + image_padding['left']
        top = outer_margin + image_padding['top']
        logo.size = (
            max(1, width - outer_margin * 2 - image_padding['left'] - image_padding['right']),
            max(1, height - outer_margin * 2 - image_padding['top'] - image_padding['bottom']))
        canvas.compose(logo, int(left), int(top))

    top = top_mgn
    if len(top_lines) > 0:
        for line in top_lines:
            twand = create_colored_text_wand(line)
            text_top = top + line.text_padding['top']
            top = draw_sized_text(
                canvas, twand, line, text_top, left_text_margin,
                right_text_margin, auto_reduce_font)
            top = text_top + measure_text_height(
                canvas, line, left_text_margin, right_text_margin)
            top += line.text_padding['bottom']

    if len(bottom_lines) > 0:
        # Draw this on a fake canvas so can determine the space required
        fake_canvas = create_canvas(width, height, bgcolor)
        footer_top = height - bottom_mgn
        for line in bottom_lines:
            line.twand = create_colored_text_wand(line)
            text_top = footer_top + line.text_padding['top']
            draw_sized_text(
                fake_canvas, line.twand, line, text_top, left_text_margin,
                right_text_margin, auto_reduce_font)
            footer_top = text_top + measure_text_height(
                fake_canvas, line, left_text_margin, right_text_margin)
            footer_top += line.text_padding['bottom']

        footer_bottom = height - bottom_mgn
        for line in reversed(bottom_lines):
            text_height = measure_text_height(
                canvas, line, left_text_margin, right_text_margin)
            text_top = footer_bottom - line.text_padding['bottom'] - text_height
            draw_sized_text(
                canvas, line.twand, line, text_top, left_text_margin,
                right_text_margin, auto_reduce_font=False)
            footer_bottom = text_top - line.text_padding['top']
        footer_top = footer_bottom
        available = (max(1, width - (content_left_margin + content_right_margin + image_padding['left'] + image_padding['right'])),
                     int(footer_top - top) - image_padding['top'] - image_padding['bottom'])
    else:
        available = (max(1, width - (content_left_margin + content_right_margin + image_padding['left'] + image_padding['right'])),
                     int(height - top) - bottom_mgn - image_padding['top'] - image_padding['bottom'])

    left_x = left_mgn
    for field in rotated_fields['left']:
        draw_rotated_field(canvas, field, left_x, top_mgn, edge_length)
        left_x += field['rail_width']

    right_x = width - right_mgn
    for field in rotated_fields['right']:
        right_x -= field['rail_width']
        draw_rotated_field(canvas, field, right_x, top_mgn, edge_length)

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
            logo = add_border(logo, image_border_width, image_border_color, bgcolor)

        left = int(max(0, content_left_margin + image_padding['left'] +
                   (available[0] - lwidth) / 2.))
        top = top + image_padding['top'] + ((available[1] - lheight) / 2.)
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
    custom_text_fields = [options.get(key, '') for key in cfg.KEY_CUSTOM_TEXT_FIELDS]
    if any(custom_text_fields):
        from calibre.ebooks.metadata.book.formatter import SafeFormat
        custom_text_fields = [
            SafeFormat().safe_format(text, mi, 'GC template error', mi).replace('<br/>','\n') if text else ''
            for text in custom_text_fields]

    fonts = options[cfg.KEY_FONTS]
    colors = options[cfg.KEY_COLORS]
    use_same_fill_color = options.get(cfg.KEY_FILL_COLORS_LINKED, True)
    
    # Determine fill colors for each text type
    title_fill = colors.get('title_fill', '#000000')
    if use_same_fill_color:
        author_fill = series_fill = title_fill
    else:
        author_fill = colors.get('author_fill', title_fill)
        series_fill = colors.get('series_fill', title_fill)
    
    content_lines = {}
    content_lines['Title'] = [
        get_textline(title_line.strip(), fonts['title'], 0, title_fill)
        for title_line in split_and_replace_newlines(title)]
    content_lines['Author'] = [
        get_textline(author_line.strip(), fonts['author'], 0, author_fill)
        for author_line in split_and_replace_newlines(author_string)]
    if series_string:
        content_lines['Series'] = [
            get_textline(series_line.strip(), fonts['series'], 0, series_fill)
            for series_line in split_and_replace_newlines(series_string)]
    for index, custom_text in enumerate(custom_text_fields, 1):
        if custom_text:
            custom_type = 'custom' if index == 1 else 'custom%d' % index
            custom_fill = title_fill if use_same_fill_color else colors.get(custom_type + '_fill', title_fill)
            content_lines['Custom Text %d' % index] = [
                get_textline(ct.strip(), fonts[custom_type], 0, custom_fill)
                for ct in split_and_replace_newlines(custom_text)]
    top_lines = []
    bottom_lines = []
    rotated_fields = {'left': [], 'right': []}
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
                line.apply_element_options(field)
            if field.get(cfg.KEY_FIELD_ROTATION, 0) in (90, 270):
                side = field.get(cfg.KEY_FIELD_ROTATION_SIDE, 'left')
                rotated_fields[side].append(lines)
            elif above_image:
                top_lines.extend(lines)
            else:
                bottom_lines.extend(lines)

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
        top_lines, bottom_lines, rotated_fields, display_image, options, image_path)
