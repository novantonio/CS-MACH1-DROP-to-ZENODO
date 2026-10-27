email_addrs = st.text_input("Contact email address", placeholder="e.g. your.email@institution.edu")

try:
    with open('gdpr.txt', 'r', encoding='utf-8') as f:
        gdpr_text = f.read()
    st.caption(gdpr_text)
except Exception as e:
    pass

# ─── Submit ───────────────────────────────────────────────────────────────────
st.markdown("---")
submit = st.button(
    "🚀 Register dataset to cs-mach1 community",
    type="primary",
    use_container_width=True,
)

if submit:
    errors = []
    if not ZENODO_TOKEN:
        errors.append("Zenodo token missing from secrets.toml.")
    if has_doi == "yes" and not existing_doi:
        errors.append("Please enter the existing dataset DOI.")
    if has_doi == "yes":
        errors.append("This version of the uploader handles new uploads only. To submit an existing DOI to cs-mach1, open the record on Zenodo and use its community-submission option.")
    if has_doi == "no" and not uploaded_file:
        errors.append("Please upload a dataset file.")
    if has_doi == "no" and not (author_first or author_last):
        errors.append("Please enter at least the first author's name.")
    if has_doi == "no" and not record_title:
        errors.append("Please provide a dataset title.")
    if not email_addrs:
        errors.append("Please provide a contact email address.")
    if has_doi == "no" and author_orcid:
        valid, msg = verify_orcid(author_orcid)
        if not valid:
            errors.append(msg)

    if errors:
        for e in errors:
            st.error(e)
        st.stop()


    with st.spinner("Uploading to Zenodo…"):
        try:
            primary_author = {
                "first": author_first,
                "last": author_last,
                "orcid": author_orcid,
                "affil": author_affil,
            }
            creators = build_creators(primary_author, collaborators)

            metadata = build_metadata(
                title=record_title,
                abstract_text=abstract,
                description_text=description,
                creators=creators,
                spatial=spatial_deployment,
                proj=project_name,
                kw=keywords,
                lat_val=st.session_state.sel_lat,
                lon_val=st.session_state.sel_lon,
                lic=license_choice,
                author_ror=selected_ror_id,
                scoop_concept_url=scoop_concept_url,
            )

            deposition = create_deposition(ZENODO_TOKEN, metadata)
            record_id = deposition["id"]
            st.info(f"📝 Zenodo deposition created (ID: {record_id})")

            file_bytes_upload = uploaded_file.getvalue()
            upload_deposition_file(
                ZENODO_TOKEN,
                deposition,
                file_bytes_upload,
                uploaded_file.name,
            )
            st.info(f"📂 File '{uploaded_file.name}' uploaded.")

            json_resp = publish_deposition(ZENODO_TOKEN, deposition)
            doi_out = json_resp.get("doi") or json_resp.get("metadata", {}).get("doi") or "n/a"
            view_url = json_resp.get("links", {}).get("html") or f"https://zenodo.org/records/{record_id}"

            # The community is requested in deposition metadata. Curators may still need to accept it.
            send_email(json_resp, email_addrs, True, ZENODO_COMMUNITY, mode="upload_success")

            st.markdown(f"""
            <div class="success-box">
                ✅ <b>Dataset published and submitted to the cs-mach1 community for review.</b><br>
                DOI: <code>{doi_out}</code><br>
                Record ID: <code>{record_id}</code><br>
                <a href="{view_url}" target="_blank" rel="noopener noreferrer">
                🔗 View record on Zenodo →</a>
            </div>""", unsafe_allow_html=True)
            st.caption(
                "The cs-mach1 community is requested in the deposition metadata. "
                "Publication does not guarantee community acceptance; the community curators may need to review the submission."
            )
            st.balloons()

        except requests.exceptions.HTTPError as e:
            response = getattr(e, "response", None)
            if response is not None:
                st.error(f"❌ Zenodo HTTP error: {response.status_code} — {response.text}")
            else:
                st.error(f"❌ Zenodo HTTP error: {e}")
        except ValueError as e:
            st.error(f"❌ {e}")
        except Exception as e:
            st.error(f"❌ Unexpected error: {e}")

# ─── Footer ───────────────────────────────────────────────────────────────────
from cs_mach1_theme import cs_mach1_footer
cs_mach1_footer("CS-MACH1 Zenodo Uploader • Marine Citizen Science Data Horizon")
