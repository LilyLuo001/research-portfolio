import numpy as np
import pytest
from estimator import _psd_covariance, InputRejected, ratio_contrast_outer_bound

def test_near_indefinite_rejected():
    v=np.eye(4); v[0,1]=v[1,0]=1+5e-11
    with pytest.raises(InputRejected): _psd_covariance(v)

def test_slight_asymmetry_rejected():
    v=np.eye(4); v[0,1]=1e-15
    with pytest.raises(InputRejected): _psd_covariance(v)

@pytest.mark.parametrize('v',[np.zeros((4,4)),np.ones((4,4)),np.eye(4),np.diag([1e-300,1e300,1,0])])
def test_valid_covariances(v):
    assert np.array_equal(_psd_covariance(v),v)

def test_bound_and_weak_denominator():
    args={'joint_critical_squared':1,'calibration_status':'SYNTHETIC_ONLY'}
    assert ratio_contrast_outer_bound([2,4,1,5],np.eye(4)*.01,**args)['kind']=='BOUNDED_INTERVAL'
    assert ratio_contrast_outer_bound([2,0,1,5],np.eye(4)*.01,**args)['kind']=='ALL_REAL'
