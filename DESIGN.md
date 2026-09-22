# Lalainluv interface

Implementation choices derived from the supplied wireframe and existing store.

- Retain the milk-tea masthead, light neutral sidebar, centered Lalainluv wordmark, image-led carousel and three collection entries.
- Rilakkuma-specialist Japanese shopping service. Use verified San-X product photography for Rilakkuma plush, character collectible blind boxes and lifestyle goods; source manifest in docs/rilakkuma-assets.md. The previous generic generated assets are retired from the storefront.
- Playfair Display wordmark (preserved existing brand type); Noto Serif TC display headings; Noto Sans TC interface/body. Browser fallbacks keep the site usable without external fonts.
- Colors in static/css/style.css: OKLCH semantic tokens for background, ink, muted text, milk-tea brand, darker brown actions, borders and sage accents.
- Desktop sidebar 222px, page gutter 40px, four-column product grid. Sidebar becomes a keyboard-accessible drawer at 960px. At 680px use two product columns and stack transaction forms.
- Buttons have explicit loading, disabled and error feedback. Private wish content is never shown publicly.
- Carousel is manual to avoid distracting automatic motion; supports buttons, keyboard arrows, touch swipes. Reduced motion disables transitions.
- Products, inventory, every carousel image, orders and contact details are managed at /manage/ using the same storefront shell and responsive CSS.
