#!/usr/bin/env python3
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "build_fixed_comparisons.py"


class FixedComparisonTest(unittest.TestCase):
    def test_denominator_multilabel_standardization_and_sparse_cancel(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"joined.csv"; output=root/"out"; rows=[]
            a_sizes=[20,20,20,20,120]; b_sizes=[120,20,20,20,20]; a_rates=[0,.25,.5,.75,1]
            for occ in range(5):
                for group,size in (("A",a_sizes[occ]),("B",b_sizes[occ])):
                    positives=int(size*a_rates[occ]) if group=="A" else 0
                    for i in range(size):
                        general=i<positives
                        row={"usable":True,"CREATED":"2020-02-01","OCCUPATION_MAJOR":f"O{occ}","CENSUS_REGION":"Northeast","COMPANY_ID":"co",
                            "OBSERVATION_END":"2020-03-01","OBSERVATION_CLOSED":True,"DATE_COMPLETE":True,"CROSSES_2022_11_30":False,
                            "tech_generative_ai_use_explicit":group=="A","tech_traditional_software_use_explicit":group=="B",
                            "tech_generative_ai_develop_explicit":group=="A" and i<10,
                            "tech_traditional_software_develop_explicit":group=="B" and i<10,
                            "tech_generative_ai_detected":group=="A","tech_predictive_ai_detected":False,"tech_unspecified_ai_detected":False}
                        for obj in ("general_work","industry_domain","specific_tool"):
                            value = general if obj != "industry_domain" else True
                            row.update({f"exp_{obj}_main":value,f"exp_{obj}_required":value,f"exp_{obj}_broad":value})
                        rows.append(row)
            with source.open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            subprocess.run([sys.executable,str(SCRIPT),"--input",str(source),"--output-dir",str(output)],check=True)
            with (output/"FIXED_COMPARISONS.csv").open() as handle:
                result=list(csv.DictReader(handle))
            def get(comparison,variant,obj):
                return next(row for row in result if row["comparison"]==comparison and row["analysis_variant"]==variant and row["experience_object"]==obj)
            general=get("C1_use","main","general_work")
            self.assertEqual((general["retained_A"],general["retained_B"]),("200","200"))
            self.assertEqual((general["A_numerator"],general["B_numerator"]),("150","0"))
            self.assertAlmostEqual(float(general["A_raw_proportion"]),.75)
            self.assertAlmostEqual(float(general["A_standardized_proportion"]),.5)
            self.assertAlmostEqual(float(general["raw_difference_minus_standardized_difference"]),.25)
            self.assertAlmostEqual(float(general["A_all_classifiable_raw_proportion"]),.75)
            industry=get("C1_use","main","industry_domain")
            self.assertEqual((industry["A_numerator"],industry["B_numerator"]),("200","200"))
            self.assertAlmostEqual(float(industry["raw_difference_A_minus_B"]),0)
            occupation=get("C1_use","main","occupation_task")
            self.assertEqual(occupation["status"],"unmeasured_D10")
            self.assertEqual(occupation["A_raw_proportion"],"")
            sparse=get("C2_develop","main","general_work")
            self.assertEqual(sparse["status"],"canceled_support")
            receipt=json.loads((output/"COMPARISON_RECEIPT.json").read_text())
            self.assertEqual(receipt["status"],"complete_with_possible_blocked_or_canceled_variants")
            self.assertEqual(receipt["input_provenance"]["content_hash"],"not_computed")
            self.assertTrue(receipt["script_sha256"])

            rows[0]["exp_general_work_main"]=None
            with source.open("w",newline="") as handle:
                writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
            output2=root/"out_null"
            subprocess.run([sys.executable,str(SCRIPT),"--input",str(source),"--output-dir",str(output2)],check=True)
            with (output2/"FIXED_COMPARISONS.csv").open() as handle:
                result2=list(csv.DictReader(handle))
            general2=next(row for row in result2 if row["comparison"]=="C1_use" and row["analysis_variant"]=="main" and row["experience_object"]=="general_work")
            self.assertEqual(general2["A_measurement_denominator"],"199")
            self.assertEqual(general2["A_unknown_boolean"],"1")
            self.assertEqual(general2["A_numerator"],"150")
            self.assertAlmostEqual(float(general2["A_raw_proportion"]),150/199)


if __name__=="__main__": unittest.main()
