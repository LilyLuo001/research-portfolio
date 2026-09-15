# Independent referee handoff

Actual role routing: **gpt-6-astra / high**; usage **NOT_OBSERVED**. Fresh analytic pass; no actual or uncertain post-treatment earnings responses read. Read the full master prompt, decisive current plan/spec/decision sections, estimation contract, permitted exposure sources and complete implementation/tests. Derived the FWL influence, equal-wave aggregation and amplitude-proof contrast before inspecting implementation. Primary G–M publisher text, BMZ, Fed conversion note, continuous-DiD authors and BDEL independently inspected.

**Overall HOLD_DESIGN; measurement and empirical precision also HOLD_DATA.** The generic econometrician FWL/covariance/aggregation mathematics is signed for its stated object. Empirical design and compute-as-contract are **not signed**. See `../review.md` for precise findings, all required challenge statuses, hashes and exit receipts.

Independent exposure support agrees: all 8,801 cells / 3,440 stocks / 30 waves, >=0.005 583 / 573 / 4; excluding Dimensional 5,638 / 2,979 / 29, >=0.005 21 / 21 / 2. Stored ownership ratio arithmetic has maximum error 0 across 8,801 cells. These are not earnings-event or independent-shock counts. Deliberate 1000x units corruption makes all-arm threshold cells 8,639. No actual exposure corruption is inferred.

Six author tests passed, exit 0. Independent full WLS/FWL coefficient error 9.21e-15; known variance 1.439058712944 versus 1.431445511247 from 50,000 independent draws; null size .04936. Consistent 1000x coefficient/variance reporting rescaling passes. Missing required input, unsigned-sponsor and canonical-path helpers fail adversarial cases; pre-effective leakage is checked, pre-announcement leakage is not. Ordinary forbidden outcome path is denied with 0 mocked opener calls.

The simulation is one invented event per stock-wave, pooled continuous target and uniform row weights. It omits research stock×wave FE, wave-specific nuisance/equal-wave effects, actual controls and economic-event reuse. Adding stock×wave FE makes this fixture rank deficient. Common-date/slope shocks, actual few-cluster inference, slower/mixed effects, common random draws, equivalence and MDEs are not implemented. Oracle Gaussian size under renamed two-group shocks is not boottest validation. Preserve honest conditional labels but do not claim a complete contract estimator.

Primary-source correction: CTV is **JFE 167 (2025),104010**, per author institution; its 2026 arXiv posting is not publication status. G–M full text is accessible at https://onlinelibrary.wiley.com/doi/full/10.1111/1475-679X.12394 and shows why midpoint drift can reflect one-sided quote/spread adjustment. This creates an interpretation requirement beyond merely substituting quotes for trades.

Smallest next action: one owner-approved primary contract reconciliation fixing comparator/population, anticipation rule, equal-wave timing object and meaningful timing/terminal margins while preserving session distinctions. Guard/code remediation can resolve audit defects but cannot close that research-design decision.

## Exact independent numerical reproduction

Run from `/Users/lilyluo/research-portfolio-p1-feasibility-20260913`. This reads implementation only, creates no files and uses synthetic outcomes only; original execution exit 0.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 - <<'PY'
import importlib.util, sys, numpy as np
from pathlib import Path
p=Path('p1/feasibility_adjudication/20260913/code/sealed_support_and_conditional_power.py')
s=importlib.util.spec_from_file_location('ref_checked',p)
m=importlib.util.module_from_spec(s); sys.modules[s.name]=m; s.loader.exec_module(m)
r=np.random.default_rng(92113); n=40
S=r.normal(size=n); P=np.tile([0.,1.],n//2); D=r.uniform(.1,1.2,size=n)
X=np.column_stack([np.ones(n),S,P,D,S*P,S*D,P*D]); Z=(S*P*D)[:,None]
w=np.linspace(.4,2.,n); A=np.column_stack([X,Z])
B=np.linalg.solve(A.T@(w[:,None]*A),A.T*w[None,:])[-1:]
y=r.normal(size=(n,6)); beta,fit=m.weighted_fwl(y,Z,X,w)
ids=np.arange(n)//2; dates=np.arange(n)%5
Omega=.5*np.eye(n)+.3*(ids[:,None]==ids)+.2*(dates[:,None]==dates)
Rh=.65**abs(np.arange(6)[:,None]-np.arange(6)); var=float((B@Omega@B.T)[0,0])
assert np.allclose(beta,B@y,atol=1e-10)
assert np.allclose(fit.beta_operator@Omega@fit.beta_operator.T,var,atol=1e-10)
b1000,f1000=m.weighted_fwl(y,Z*1000,X,w)
assert np.allclose(1000*b1000,beta,atol=1e-10)
assert np.allclose(1e6*(f1000.beta_operator@Omega@f1000.beta_operator.T),var,atol=1e-10)
f=np.array([.25,.5,.7,.85,.95,1.]); L=np.column_stack([np.eye(5),-f[:5,None]])
assert np.max(abs(L@(.3*f)))<1e-15
e=r.normal(size=(50000,n,6))
e=np.einsum('ij,rjh->rih',np.linalg.cholesky(Omega),e)@np.linalg.cholesky(Rh).T
b=np.einsum('kn,rnh->rkh',B,e)[:,0,:]; q=b@L.T
iq=np.linalg.inv(L@(var*Rh)@L.T); wald=np.einsum('ri,ij,rj->r',q,iq,q)
print({'max_beta_error':float(abs(beta-B@y).max()),'variance':var,
       'mc_variance':float(np.var(b[:,0],ddof=1)),
       'size':float(np.mean(wald>11.0704976935)),'reps':50000})
PY
```
