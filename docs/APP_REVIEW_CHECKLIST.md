# Meta App Review Checklist (Min-Pass)

Use this as a reviewer-reproducible pre-submit check.

## App Domains

- [ ] In Meta App Dashboard -> Settings -> Basic, set `App Domains` to include:
  - [ ] `facebook-login-oaut.streamlit.app`
  - [ ] (Optional) `localhost` for local testing

## Valid OAuth Redirect URIs

- [ ] In Meta App Dashboard -> Facebook Login -> Settings -> `Valid OAuth Redirect URIs`, add exact Streamlit callback URLs:
  - [ ] `https://facebook-login-oaut.streamlit.app/Login`
  - [ ] `http://localhost:8501/Login` (local test, if used)
- [ ] Ensure app env `OAUTH_REDIRECT_URI` matches one registered URI exactly (including `/Login`, scheme, and host).

## Privacy Policy URL

- [ ] Set **Privacy Policy URL** to: `https://facebook-login-oaut.streamlit.app/Privacy`
- [ ] URL is publicly accessible **without login**.

## Data Deletion Instructions URL

- [ ] Set **Data Deletion Instructions URL** to: `https://facebook-login-oaut.streamlit.app/Data_Deletion`
- [ ] URL is publicly accessible **without login**.

## Screencast Outline (Permission -> In-App Proof)

- [ ] `instagram_basic` -> `/Login` (OAuth grant) and `/Live_Insights` profile/basic account section.
- [ ] `instagram_manage_insights` -> `/Dashboard` metrics/charts and `/Live_Insights` business insights section.
- [ ] `pages_show_list` -> `/Login` connected Page discovery flow and `/Live_Insights` pages list section.
- [ ] `pages_read_engagement` -> `/Dashboard` audience demographics and `/Live_Insights` audience data section.
- [ ] `business_management` -> `/Login` Business Manager fallback flow (`/me/businesses`, `/{business-id}/owned_pages`).
- [ ] Keep one continuous 2-3 minute recording showing login, permission grant, each mapped section, then `/Privacy` and `/Data_Deletion`.
