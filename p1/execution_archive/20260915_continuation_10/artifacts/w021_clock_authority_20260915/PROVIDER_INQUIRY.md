# Provider inquiry — WRDS I/B/E/S actuals clock semantics

Status: **READY_TO_SEND; NOT SENT BY CODEX**

Subject: Field semantics for `ibes.actu_epsus.anndats` and `anntims`

We are using an archived WRDS I/B/E/S U.S. actuals extract from
`ibes.actu_epsus` over the full coverage of a frozen research manifest. Before
classifying earnings announcements relative to historical U.S. exchange
sessions, please confirm the following for this WRDS delivery/version:

1. **Timezone and DST.** Do `anndats` and `anntims` preserve an I/B/E/S
   direct-delivery convention such as season-dependent U.S. Eastern time? If
   not, what timezone and daylight-saving rule applies?
2. **Operational timestamp.** Does `anndats`/`anntims` represent the issuer's
   first public earnings release, a source-document report time, I/B/E/S
   collection/receipt time, database activation time, or another event? Please
   distinguish it from `actdats`/`acttims`.
3. **Precision and uncertainty.** Are seconds retained? Are displayed minutes
   rounded or truncated? Are any times defaulted or imputed, including midnight
   values? What uncertainty should be assigned to a populated `anntims` value?
4. **Corrections and revisions.** When actuals are corrected or revised, are
   `anndats`/`anntims` overwritten, retained as the original announcement, or
   reassigned? Is revision history available in this WRDS table or a companion
   table?

Please cite the applicable I/B/E/S/WRDS guide name, version/date and section, or
identify the exact delivery-specific data dictionary. A statement about an
Eikon/Workspace field or a current API is helpful only if it explicitly applies
to the WRDS `ibes.actu_epsus` historical delivery.

The requested answer concerns metadata definitions only; no observations,
financial values or credentials are included in this inquiry.

## Required receipt

When the provider answers, preserve:

- ticket/case identifier and response date;
- responder/team and provider;
- quoted field/table names and delivery/version;
- attached guide/version or official URL;
- SHA256 of the saved response/attachment;
- a four-row adjudication mapping each question above to
  `CONFIRMED`, `CONTRADICTED`, or `UNRESOLVED`.

Do not infer answers from silence. If any of timezone, operational timestamp or
uncertainty remains unresolved, keep the affected release keys `UNKNOWN`.
