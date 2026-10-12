# Frontend

- `index.html`: standalone generated export of the current interactive design.
- `src/design-preview.fragment.html`: editable design source.

Open `index.html` in a browser for the existing simulation. External fonts/icons may need internet. It currently has no backend connection or real authentication. Never enter real Razorpay credentials into its sample login.

After source edits, regenerate the standalone export; the fragment and export are not automatically synchronised. There is currently no build script or dependency manifest.

The future application will render merchant setup, opportunities, plan/action review, activity, supervision, analytics and settings using backend-authorised state. Framework selection remains pending; this reorganisation does not convert the preview into a production application.
