# Nortica brand kit v2

Imported from `nortica-brand-kit-v2.zip`. SVGs are the editable sources; the
original exports, avatars, app icons, banners, social images and favicons are
kept together here.

## Integration

- Repository README: light/dark horizontal SVG wordmarks.
- Live installer launcher: `app-icon-dark-512.png`.
- GRUB/Syslinux backgrounds: `logo-horizontal-dark.png` over the wallpaper,
  with the brand's olive selection colors.
- Help/ticket launchers: copies of `app-icon-dark-512.png` in the config repo.
- Default wallpaper: `config/wallpapers/nortica.png`, imported separately from
  `nortica_wallpaper1.png`.

## Upstream notes

Primary font: Code New Roman Bold. The editable SVG wordmarks request this font with DejaVu Sans Mono fallback. Code New Roman is not installed in the generation environment, so PNG wordmarks use a fallback and are provisional. Install Code New Roman locally and regenerate the PNGs with Inkscape, e.g. `inkscape logo-horizontal-dark.svg --export-filename=logo-horizontal-dark.png`. Symbol-only assets remain unchanged. Palette: #b8bb26, #282828, #79740e, #fbf1c7.
