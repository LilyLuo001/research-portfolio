# GDPval duration-pilot annotator qualification framework

**Frozen before recruitment and before pilot responses.** This framework
operationalizes “qualified human” for every pilot and production assignment.
An AI system, anonymous unverified account, or general survey respondent does
not qualify merely by asserting familiarity.

## Assignment-level eligibility

For each task, all of the following are required:

1. **Exact occupation/domain:** at least two years of current or recent
   hands-on professional experience in the task's released GDPval occupation,
   or at least two years directly supervising that work. Sector experience
   must also match the task's GDPval sector.
2. **Recency:** relevant work occurred in 2016 or later. Older experience alone
   is insufficient unless the qualification framework is prospectively amended
   before that person sees a task.
3. **Deliverable/tool competence:** documented experience with the task's
   frozen format class: spreadsheet/tabular, document, presentation,
   code/data, media/design, mixed, or other/text.
4. **Regulated work:** when competent completion would ordinarily require a
   professional license or regulated-domain authority, the annotator must hold
   the relevant active credential or document recent direct supervision of
   credentialed work. The private qualification reviewer records the
   task-specific credential requirement before assignment.
5. **Independence and conflicts:** no involvement in GDPval task construction,
   no financial/personal conflict affecting the estimate, no communication
   with the other two task annotators, and no access to their responses.
6. **Human verification and governance:** human identity and experience are
   reviewed by authorized project staff; consent, confidentiality, payment,
   and any necessary IRB determination are complete before task access.

The executable check is `duration_annotator_qualification.py`. A failed field
cannot be waived after the annotator's duration estimate is seen.

## Staffing rules

- Every task receives three independently completed round-1 estimates from
  three different qualified humans.
- A fourth human, qualified under the same task-specific rule, must be
  available for triggered adjudication.
- A person may cover multiple tasks only where separately qualified for every
  occupation, sector, format, and credential requirement. Broad self-described
  “AI expertise” is not a substitute for occupational experience.
- Prefer hands-on professionals over supervisors where both are available.
- No task is released until the private roster contains at least three eligible
  round-1 people and one eligible potential adjudicator for that assignment.

## Records and privacy

Private storage contains the eligibility evidence, consent/payment records,
conflicts, identity verification, and assignment matrix. Git receives only
aggregate counts by experience band, role type, sector coverage, qualification
status, and hashes. Names, emails, employers, CVs, licenses, payment details,
and annotator codes must not be committed.

Current qualified roster: **0 people verified**. Consequently, recruitment and
pilot agreement are not yet evaluable.
