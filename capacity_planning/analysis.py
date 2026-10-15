"""Calendar-only aggregate service-capacity planning; not fleet/station optimization."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from common import dataset,save_report
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error

ROOT=Path(__file__).resolve().parent
FEATURES=['hr','weekday','workingday','holiday','mnth','time_index']

def asymmetric_loss(actual,capacity,shortage_cost,idle_cost=1):
    actual=np.asarray(actual);capacity=np.asarray(capacity)
    if shortage_cost<=0 or idle_cost<=0 or np.any(capacity<0):raise ValueError('Invalid inputs')
    return float((np.maximum(actual-capacity,0)*shortage_cost+np.maximum(capacity-actual,0)*idle_cost).mean())

def summarize(y,capacity,ratio):
    return {'mean_capacity':float(np.mean(capacity)),'mean_uncovered_requests':float(np.maximum(y-capacity,0).mean()),
            'mean_idle_capacity':float(np.maximum(capacity-y,0).mean()),
            'hour_coverage_rate':float(np.mean(y<=capacity)),
            'assumed_cost_per_hour':asymmetric_loss(y,capacity,ratio)}

def features(df):
    result=df[FEATURES].copy()
    assert not set(result)&{'cnt','casual','registered','temp','atemp','hum','windspeed','weathersit'}
    return result

def main():
    path,digest=dataset(ROOT,275,'bike+sharing+dataset','hour.csv')
    df=pd.read_csv(path)
    df['timestamp']=pd.to_datetime(df.dteday)+pd.to_timedelta(df.hr,unit='h')
    assert not df.timestamp.duplicated().any() and (df.cnt==df.casual+df.registered).all()
    df=df.sort_values('timestamp');df['time_index']=(df.timestamp-pd.Timestamp('2011-01-01')).dt.total_seconds()/86400
    train=df[df.timestamp<'2012-07-01'];val=df[(df.timestamp>='2012-07-01')&(df.timestamp<'2012-10-01')];test=df[df.timestamp>='2012-10-01']
    X=features(train); y=test.cnt.to_numpy()
    median=HistGradientBoostingRegressor(loss='absolute_error',max_iter=120,max_leaf_nodes=15,l2_regularization=5,random_state=7).fit(X,train.cnt)
    prediction=np.maximum(median.predict(features(test)),0)
    ratios=[2,5,10];results={}; selections={};predictions={}
    for ratio in ratios:
        q=ratio/(ratio+1)
        candidate_results=[];models=[]
        for leaves in [7,15]:
            model=HistGradientBoostingRegressor(loss='quantile',quantile=q,max_iter=120,max_leaf_nodes=leaves,l2_regularization=5,random_state=7).fit(X,train.cnt)
            p=np.maximum(model.predict(features(val)),0)
            candidate_results.append(asymmetric_loss(val.cnt,p,ratio));models.append(model)
        pick=int(np.argmin(candidate_results));selections[str(ratio)]={'quantile':q,'max_leaf_nodes':[7,15][pick],'validation_losses':candidate_results}
        # Baseline and model use exactly the same training period; no test fitting.
        constant=np.repeat(float(train.cnt.quantile(q)),len(test))
        grouped=train.groupby(['hr','workingday']).cnt.quantile(q)
        seasonal=np.array([grouped.get((r.hr,r.workingday),train.cnt.quantile(q)) for r in test.itertuples()])
        modelp=np.maximum(models[pick].predict(features(test)),0)
        predictions[str(ratio)]=modelp
        results[str(ratio)]={name:summarize(y,p,ratio) for name,p in [('constant',constant),('hour_workday',seasonal),('quantile_model',modelp)]}
    mainresult=results['5']; cost_delta=1-mainresult['quantile_model']['assumed_cost_per_hour']/mainresult['hour_workday']['assumed_cost_per_hour']
    metrics={'source_rows':len(df),'train_rows':len(train),'validation_rows':len(val),'test_rows':len(test),
        'source_archive_sha256':digest,'test_start':str(test.timestamp.min()),'test_end':str(test.timestamp.max()),
        'calendar_model_test_mae':round(float(mean_absolute_error(y,prediction)),3),
        'ratio_5_model_scenario_cost':round(mainresult['quantile_model']['assumed_cost_per_hour'],3),
        'ratio_5_seasonal_scenario_cost':round(mainresult['hour_workday']['assumed_cost_per_hour'],3),
        'ratio_5_scenario_cost_change_pct':round(cost_delta*100,2),
        'ratio_5_hour_coverage_rate':round(mainresult['quantile_model']['hour_coverage_rate'],4),
        'missing_hour_slots':int(len(pd.date_range(df.timestamp.min(),df.timestamp.max(),freq='h'))-len(df)),
        'selections':selections,'cost_sensitivity':results,'features':FEATURES,
        'limitations':['Demand is observed rentals, not latent demand or stockouts.','Capacity means hypothetical hourly service throughput, not physical fleet size.','No trip durations, station balances or rebalancing costs available.','Training precedes 2012 Q3 validation and Q4 test; growth/seasonality can cause drift.','Shortage/idle costs are scenario assumptions, not measured savings.','Missing recorded hours are not imputed as zero.']}
    folder=ROOT/'reports';folder.mkdir(exist_ok=True)
    out=pd.DataFrame({'timestamp':test.timestamp,'observed_rentals':y,'median_prediction':prediction,'capacity_ratio5':predictions['5']})
    out.to_csv(folder/'holdout_capacity.csv',index=False)
    pd.DataFrame([{'ratio':ratio,'policy':name,**r} for ratio,policies in results.items() for name,r in policies.items()]).to_csv(folder/'scenario_comparison.csv',index=False)
    save_report(ROOT,'Demand and Service Capacity Planning',
        f"Compared calendar-based capacity policies on {len(test):,} held-out hours. At an assumed 5:1 shortage-to-idle cost, model scenario cost differs by {cost_delta:.1%} from the hour/workday policy (positive means lower cost).",[
        ('Decision','Test calendar-based capacity guidance in shadow mode before operational use. Review both under-capacity and idle-capacity exposure across the 2:1, 5:1 and 10:1 assumed cost ratios; do not select a policy from mean forecast error alone.'),
        ('Method','Trained before July 2012, selected tree complexity on July–September 2012 and tested once on October–December 2012. Quantile targets are shortage cost divided by shortage plus idle cost. Compared against constant and hour/workday quantile baselines.'),
        ('Availability and leakage','Uses calendar and elapsed-time inputs only. Excludes actual weather because future weather is not known without forecasts; excludes registered/casual rentals because they sum to the target. Missing observation hours are not treated as zero demand.'),
        ('Interpretation','This is an aggregate hourly service-throughput scenario, not an optimal bike fleet or station allocation. Observed completed rentals omit lost demand and do not provide trip duration, fleet inventory or station constraints.'),
        ('Pilot and safeguards','Validate future availability, operational cost estimates and local demand. Run a shadow pilot with pre-agreed coverage, idle-capacity and stability thresholds; retain a simple policy fallback and review drift monthly.'),
        ('Source','Fanaee-T (2013), Bike Sharing, UCI, CC BY 4.0. https://doi.org/10.24432/C5W894')],metrics)
    print({k:v for k,v in metrics.items() if not isinstance(v,(dict,list))})

if __name__=='__main__':main()

