# External architecture admission rule

Status: written after prior YAX outcomes were opened, but before fitting either
Webb AI or OECD exposure to the YAX outcome. Any admitted result is
**post-outcome exploratory** and does not alter the confirmatory family.

An external score is admitted to the revised outcome grid only if all of the
following conditions hold without inspecting its outcome coefficient:

1. a public, version-identifiable source file and primary construct document
   are available and their hashes/locators are recorded;
2. the score measures potential occupational exposure to AI capabilities or AI
   task substitution, rather than realized adoption or an undifferentiated
   automation probability;
3. its occupational code can be routed to six-digit SOC 2018 and then Census
   2018 without occupation-title matching;
4. Census-occupation values use only fully observed component scores; missing
   components are not silently dropped and remaining weights are not
   renormalized;
5. on the frozen pre-period occupation universe, retained occupations cover at
   least 80 percent of pre-period employment weight and yield four distinct
   employment-weighted quintile cut points; and
6. the score is fitted on its disclosed support with the frozen YAX outcome,
   age comparison, calendar, fixed effects, Webb-software conditioning, and
   occupation-cluster wild-score procedure. A common-support comparison with
   the frozen beta measure is also required.

The 80-percent rule is a minimum external-validity safeguard, not a claim that
80 percent is sufficient for national representativeness. Failure on any item
produces a documented exclusion rather than imputation or a result-dependent
exception. Frey--Osborne remains an automation-risk comparator and is not
eligible under item 2. LLM-annotated alternatives not already in the frozen
family are outside this targeted admission exercise unless all six conditions
are independently satisfied.

