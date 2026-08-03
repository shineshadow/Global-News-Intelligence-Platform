# Dark Operations Theme

This directory is the self-contained presentation package for the temporary
GNI dark operations theme:

- `header.html` owns the shared banner markup.
- `theme.css` owns the theme palette, component overrides, banner dimensions,
  and responsive navigation.

The shared application template selects this package in `base.html`. A future
theme can be added as a sibling directory and activated by changing only the
theme stylesheet path, body class, and header include in that template.

The banner uses the general image assets in `app/web/static/img/`. Its desktop
frame is `80.5rem × 26.8125rem`; narrower screens retain the source aspect
ratio without horizontal overflow.
