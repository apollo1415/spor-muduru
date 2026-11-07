"""Transparent exploratory distribution models. Not calibrated betting probabilities."""
import math
def poisson_tail(lam,threshold):
    """P(X > threshold), for nonnegative integer threshold."""
    if lam<0 or threshold<0:raise ValueError("invalid Poisson arguments")
    term=math.exp(-lam)
    cdf=term
    for k in range(1,threshold+1):
        term*=lam/k
        cdf+=term
    return max(0.,min(1.,1.-cdf))
def estimate_total(home_for,home_against,away_for,away_against,minimum=5):
    """Home/away observed counts; blends attacking and opposing defensive means."""
    arrays=[home_for,home_against,away_for,away_against]
    if min(map(len,arrays))<minimum:return None
    mean=lambda v:sum(v)/len(v)
    return (mean(home_for)+mean(away_against))/2+(mean(away_for)+mean(home_against))/2
def add_count_markets(output,history,home,away,sample,metric,homefield,awayfield,thresholds):
    hf=sample(history,home,True,homefield)
    ha=sample(history,home,True,awayfield)
    af=sample(history,away,False,awayfield)
    aa=sample(history,away,False,homefield)
    n=min(map(len,[hf,ha,af,aa]))
    output["n_"+metric]=n
    lam=estimate_total(hf,ha,af,aa)
    if lam is None:return
    output["lambda_"+metric]=round(lam,3)
    for threshold in thresholds:
        output["p_"+metric+"_over_"+str(threshold)]=round(poisson_tail(lam,threshold),5)
    output["note_"+metric]="Exploratory Poisson count baseline; overdispersion not calibrated"
