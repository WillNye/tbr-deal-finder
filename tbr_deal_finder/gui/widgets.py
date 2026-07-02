from typing import List, Optional

import flet as ft

GRID_COVER_HEIGHT = 200


def truncate_title(title: str, limit: int = 60) -> str:
    return f"{title[:limit]}..." if len(title) > limit else title


def _cover_placeholder(width: int, height: int) -> ft.Container:
    """A book-icon placeholder used when a cover is missing or fails to load.
    """
    return ft.Container(
        width=width,
        height=height,
        border_radius=4,
        bgcolor=ft.Colors.GREY_200,
        alignment=ft.alignment.center,
        content=ft.Icon(
            ft.Icons.MENU_BOOK,
            color=ft.Colors.GREY_400,
            size=max(12, int(min(width, height) * 0.5)),
        ),
    )


def cover_image(image_url: Optional[str], width: int = 40, height: int = 60) -> ft.Control:
    """Book cover thumbnail shown to the left of a title.
    """
    if not image_url:
        return _cover_placeholder(width, height)

    return ft.Image(
        src=image_url,
        width=width,
        height=height,
        fit=ft.ImageFit.CONTAIN,
        border_radius=4,
        error_content=_cover_placeholder(width, height),
    )


def cover_image_for_format(
    image_url: Optional[str], book_format, height: int = GRID_COVER_HEIGHT
) -> ft.Control:
    """Cover sized to the format's natural aspect so it fills the box without
    letterboxing: audiobook art is square (1:1), ebook art is portrait (2:3).
    """
    fmt = getattr(book_format, "value", book_format)
    if fmt == "E-Book":
        width = round(height * 2 / 3)  # portrait 2:3
    else:
        width = height  # square (audiobook, and N/A / unknown)
    return cover_image(image_url, width=width, height=height)


def book_tile_card(
    cover: ft.Control,
    info: List[ft.Control],
    *,
    on_click=None,
    overlay: Optional[ft.Control] = None,
    trailing: Optional[ft.Control] = None,
) -> ft.Card:
    """A grid tile: cover on the left, a column of `info` controls on the right,
    wrapped in a Card.
    """
    row_children = [
        cover,
        ft.Column(
            info,
            spacing=4,
            expand=True,
            alignment=ft.MainAxisAlignment.CENTER,
        ),
    ]
    if trailing is not None:
        row_children.append(trailing)

    row = ft.Row(
        row_children,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=12,
    )

    content = row if overlay is None else ft.Stack([
        row,
        ft.Container(content=overlay, top=0, right=0),
    ])

    return ft.Card(
        content=ft.Container(
            content=content,
            padding=10,
            on_click=on_click,
        )
    )
