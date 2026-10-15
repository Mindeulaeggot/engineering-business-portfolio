"""Chronological campaign prioritization; NOT causal uplift or realized profit."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import dataset, save_report
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

ROOT = Path(__file__).resolve().parent
# Only previous-campaign history, planned contact context and macro variables.
# Explicitly exclude call duration, current-campaign contacts and demographic/credit variables.
FEATURES = ['previous','pdays','poutcome','contact','month','day_of_week',
            'emp.var.rate','cons.price.idx','cons.conf.idx','euribor3m','nr.employed']
CAT = ['poutcome','contact','month','day_of_week']
NUM = [x for x in FEATURES if x not in CAT]

def top_budget(y, scores, fraction):
    y, scores = np.asarray(y), np.asarray(scores)
    if len(y) != len(scores) or not 0 < fraction <= 1 or not len(y):
        raise ValueError('Invalid budget or arrays')
    k = max(1, int(np.floor(len(y)*fraction)))
    chosen = np.argsort(-scores, kind='stable')[:k]
    successes = int(y[chosen].sum())
    return {'contacts': k, 'observed_positives': successes,
            'precision': successes/k, 'recall': successes/max(1,int(y.sum())),
            'lift_vs_random_expectation': (successes/k)/max(float(y.mean()),1e-12)}

def scenario(contacts, positives, margin, cost):
    if min(contacts, positives, margin, cost) < 0 or positives > contacts:
        raise ValueError('Invalid scenario inputs')
    return positives*margin - contacts*cost

def split_ordered(df):
    a, b = int(len(df)*.6), int(len(df)*.8)
    return df.iloc[:a], df.iloc[a:b], df.iloc[b:]

def main():
    path, digest = dataset(ROOT,222,'bank+marketing','bank-additional-full.csv')
    df = pd.read_csv(path, sep=';')
    assert len(df)==41188 and set(df.y)=={'yes','no'}
    assert 'duration' not in FEATURES and 'campaign' not in FEATURES
    train, val, test = split_ordered(df)
    target = lambda frame: (frame.y=='yes').astype(int).to_numpy()
    prep = lambda: ColumnTransformer([('cat',OneHotEncoder(handle_unknown='ignore',sparse_output=False),CAT),('num',StandardScaler(),NUM)])
    candidates = {
        'logistic_regression': make_pipeline(prep(),LogisticRegression(max_iter=1200,random_state=7)),
        'random_forest': make_pipeline(prep(),RandomForestClassifier(n_estimators=180,min_samples_leaf=35,max_depth=10,random_state=7,n_jobs=2)),
    }
    val_scores = {}
    for name,model in candidates.items():
        model.fit(train[FEATURES], target(train))
        val_scores[name] = float(average_precision_score(target(val), model.predict_proba(val[FEATURES])[:,1]))
    selected = max(val_scores,key=val_scores.get)
    model = candidates[selected]
    # Model remains trained only on first 60%; neither refit nor tune on final test.
    y = target(test); scores = model.predict_proba(test[FEATURES])[:,1]
    budgets = {str(f):top_budget(y,scores,f) for f in [.1,.2,.3,.5,1.]}
    # Uniform, seeded tie-break within the simple rule's two tiers; never use labels.
    baseline_scores = (test.poutcome=='success').astype(float).to_numpy()+np.random.default_rng(7).uniform(0,1e-6,len(test))
    history = top_budget(y,baseline_scores,.2)
    chosen = budgets['0.2']
    # Day blocks do not exist as exact dates here; row-level bootstrap is descriptive,
    # not a valid time-series confidence interval, so do not report it as one.
    scenarios = []
    for margin in [20,50,100]:
        for cost in [1,3,5]:
            scenarios.append({'assumed_margin':margin,'assumed_cost':cost,'illustrative_value':scenario(chosen['contacts'],chosen['observed_positives'],margin,cost)})
    metrics = {'source_rows':len(df),'train_rows':len(train),'validation_rows':len(val),'test_rows':len(test),
        'source_archive_sha256':digest,'selected_model':selected,'validation_average_precision':val_scores,
        'train_positive_rate':round(float(target(train).mean()),6),'validation_positive_rate':round(float(target(val).mean()),6),
        'test_positive_rate':round(float(y.mean()),6),'test_average_precision':round(float(average_precision_score(y,scores)),6),
        'test_roc_auc':round(float(roc_auc_score(y,scores)),6),'test_brier_score':round(float(brier_score_loss(y,scores)),6),
        'budget_20pct_contacts':chosen['contacts'],'budget_20pct_precision':round(chosen['precision'],6),
        'budget_20pct_recall':round(chosen['recall'],6),'budget_20pct_lift':round(chosen['lift_vs_random_expectation'],3),
        'prior_success_baseline_20pct_precision':round(history['precision'],6),
        'features':FEATURES,'budget_results':budgets,'scenarios':scenarios,
        'limitations':['Historical contacted population only; no randomized no-contact control.','Not causal uplift, incremental deposits or deployable profit.','Row order is chronological per UCI; no customer IDs or exact timestamps.','Macro drift and repeated clients can affect evaluation.','Excluding demographic variables does not establish fairness.','Planned contact context must be known at scoring time.']}
    folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    pd.DataFrame({'row_position':test.index,'observed_subscription':y,'score':scores}).to_csv(folder/'holdout_scores.csv',index=False)
    pd.DataFrame([{'fraction':f,**v} for f,v in budgets.items()]).to_csv(folder/'budget_curve.csv',index=False)
    save_report(ROOT,'Campaign Budget Prioritization',
        f"A fixed 20% contact budget retrieves {chosen['recall']:.1%} of observed positive labels in the final chronological holdout. This is a retrospective ranking result, not incremental conversion.",[
        ('Decision', f"The selected model does not justify deployment: at a 20% contact budget its test precision is {chosen['precision']:.1%}, versus {history['precision']:.1%} for a simple prior-success rule. Treat this as a model-risk finding, not a predictive success story. Validate the rule prospectively and pre-register a randomized, consent-compliant pilot with incremental response, opt-outs and subgroup monitoring."),
        ('Design',f'Used 41,188 UCI records in original date order, split 60/20/20. Excluded duration (post-call leakage), current-campaign contact count and demographic/credit attributes. Chose {selected} using validation average precision; retained final 20% for one test.'),
        ('Budget trade-off',f"At 20% budget, observed precision is {chosen['precision']:.1%} versus {y.mean():.1%} random-selection expectation. A prior-success-history baseline gives {history['precision']:.1%}; both baselines must be reviewed before model complexity is justified."),
        ('Economics and sensitivity','Scenario grid assumes 20/50/100 currency units of contribution per observed positive and 1/3/5 per contact. These values are hypothetical, not measured customer lifetime value or marketing ROI; selection bias prevents causal interpretation.'),
        ('Risks','Historical selected population, temporal/macroeconomic drift, untracked repeated clients, context availability and potential proxy discrimination. A strong AUC alone is insufficient for production.'),
        ('Source','Moro, Rita & Cortez (2014), Bank Marketing, UCI, CC BY 4.0. https://doi.org/10.24432/C5K306')],metrics)
    print({k:v for k,v in metrics.items() if not isinstance(v,(list,dict))})

if __name__=='__main__':main()

