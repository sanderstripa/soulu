# Native Settings overlay

`SettingsOverlay` owns a popup clipped to the browser client area and a separate CEF Settings browser. It blocks background input without replacing the tab, navigating the active page or recreating its session. The host follows owner geometry, fullscreen and DPI.

The panel starts hidden above the clipping region. Settings waits for Onest and initial layout, requests measured height, and sends `settings.ready` with that height. Native code applies height before opening, preventing a full-size first frame on compact Home.

Home uses intrinsic content height bounded 160–800 logical pixels. Sections use an 800px workspace bounded by the owner client area. Height retargets from the displayed value using a 380ms cosine ease. Resize updates panel clip/placement without rebuilding the backdrop; close cancels height animation.

Opening/closing use a Settings-specific 380ms ease, or 90ms when Windows disables animation. Backdrop and composition shadow follow progress. The shadow is suppressed while the panel is entirely above the clipping region. Other surfaces retain their existing motion/shadow behavior.

Sections use the accepted 320ms fade with 45ms delay and small translation, independently of generic viewport-resize cancellation. They do not clone interactive controls. Reduced motion retains a brief fade without movement.

Close blurs the field and waits for saves. The blocker remains during closing; host lifetime extends until CEF finishes closing, and focus returns to the original browser. Profile changes refresh the existing session after pending work is flushed. The design-review companion is outside the production implementation and is never packaged.
