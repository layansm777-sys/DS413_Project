import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pycountry

st.set_page_config(page_title='Global Education Dashboard', layout='wide')
COUNTRY = 'Countries and areas'
LEVELS = {'Primary':'Primary','Lower Secondary':'Lower_Secondary','Upper Secondary':'Upper_Secondary'}
MALE, FEMALE = '#2563A6', '#E17A37'

@st.cache_data
def load_data():
    data = pd.read_excel('Global_Education_2.xlsx', sheet_name='in')
    data.columns = data.columns.str.strip()
    return data

df = load_data()
st.title('Global Education Trends')
st.caption('DS413 | Phase 2 Interactive Analytics Dashboard')
with st.sidebar:
    st.header('Filters')
    countries = st.multiselect('Country / Area', sorted(df[COUNTRY].dropna().unique()))
    gender = st.selectbox('Gender', ['Both', 'Male', 'Female'])
    level = st.selectbox('Education Level', list(LEVELS))
    st.caption('No country selected = all countries. Gender applies to gender-specific plots; Q4 specifically studies females.')
filtered = df[df[COUNTRY].isin(countries)].copy() if countries else df.copy()
selected = ['Male','Female'] if gender == 'Both' else [gender]
code = LEVELS[level]

def reported(frame, col):
    return pd.to_numeric(frame[col], errors='coerce').replace(0, np.nan)

def mean_cols(frame, cols):
    return pd.concat([reported(frame,c) for c in cols],axis=1).stack().mean()

def fmt(v):
    return f'{v:.1f}%' if pd.notna(v) else 'N/A'

def show(fig, key):
    fig.update_layout(template='plotly_white', margin=dict(l=35,r=25,t=70,b=40))
    st.plotly_chart(fig, width='stretch', key=key)

st.info('Data methodology: Q1, Q2, Q3 and KPI summaries exclude zero-valued educational indicators as potentially unreported. Q4 reproduces the Phase 1 mean-imputation approach: zero or missing values in birth rate and female primary completion are replaced with their full-dataset nonzero column means. Imputation markers identify values replaced by THIS dashboard, not independently verified original missing-value flags.')
completion = [f'Completion_Rate_{code}_{g}' for g in selected]
oosr = [f'OOSR_{code}_Age_{g}' for g in selected]
cols = st.columns(4)
cols[0].metric('Countries / Areas', filtered[COUNTRY].nunique())
cols[1].metric(f'{level} Completion',fmt(mean_cols(filtered,completion)))
cols[2].metric(f'{level} Out-of-School',fmt(mean_cols(filtered,oosr)))
if gender == 'Both':
    m,f = [reported(filtered,f'Completion_Rate_{code}_{g}') for g in ('Male','Female')]
    cols[3].metric('Mean Absolute Gender Gap',fmt((f-m).abs().mean()))
else:
    cols[3].metric('Selected Gender',gender)

st.subheader('Q1 — Where Are Children Most Likely to Be Out of School?')
st.caption('Choropleth and top-ten bar chart use the selected education level, countries, and gender. Zero-valued indicators are excluded.')
q1 = pd.DataFrame({'Country':filtered[COUNTRY], 'OOSR':pd.concat([reported(filtered,c) for c in oosr],axis=1).mean(axis=1)})
fixes={'The Bahamas':'BHS','Brunei':'BRN','Cape Verde':'CPV','Ivory Coast':'CIV','Democratic Republic of the Congo':'COD','The Gambia':'GMB','Guinea0Bissau':'GNB','Vatican City':'VAT','Republic of Ireland':'IRL','Russia':'RUS','Turkey':'TUR','Palestinian National Authority':'PSE','East Timor':'TLS'}
def iso3(name):
    if name in fixes: return fixes[name]
    try: return pycountry.countries.lookup(str(name)).alpha_3
    except LookupError: return None
q1['ISO3']=q1['Country'].map(iso3)
q1=q1.dropna(subset=['OOSR'])
q1['Level']=pd.cut(q1['OOSR'],[-np.inf,10,30,50,np.inf],right=False,labels=['Low (<10%)','Moderate (10–30%)','High (30–50%)','Very high (≥50%)'])
if not q1.empty:
    fig=px.choropleth(q1.dropna(subset=['ISO3']),locations='ISO3',color='Level',hover_name='Country',hover_data={'OOSR':':.1f','ISO3':False},category_orders={'Level':['Low (<10%)','Moderate (10–30%)','High (30–50%)','Very high (≥50%)']},color_discrete_sequence=['#D8D0EA','#A99ACB','#7464A5','#42326D'],title=f'Out-of-School Rates — {level} ({gender})')
    fig.update_geos(projection_type='natural earth',showframe=False)
    show(fig,'q1map')
    if q1['ISO3'].isna().any(): st.caption(f"{q1['ISO3'].isna().sum()} locations could not be matched to map codes; they remain available in the bar chart.")
    top=q1.nlargest(10,'OOSR').sort_values('OOSR')
    fig=px.bar(top,x='OOSR',y='Country',orientation='h',text='OOSR',title='Top 10 Out-of-School Rates',labels={'OOSR':'Out-of-school rate (%)','Country':''})
    fig.update_traces(marker_color=['#9C9C9C']*(len(top)-1)+['#B34D4D'],texttemplate='%{text:.1f}%')
    show(fig,'q1bar')
else: st.warning('No reported out-of-school values for these filters.')

st.subheader('Q2 — Gender Gap in Education')
st.caption('Both genders are required to calculate a gap. The gender filter does not remove either group from this comparison.')
def paired(frame, level_name, kind):
    k=LEVELS[level_name]
    prefix=f'Completion_Rate_{k}_' if kind=='completion' else f'OOSR_{k}_Age_'
    d=pd.DataFrame({'Country':frame[COUNTRY], 'Male':reported(frame,prefix+'Male'),'Female':reported(frame,prefix+'Female')}).dropna()
    d['Gap']=d['Female']-d['Male']
    return d
summary=[]
for kind in ['completion','oosr']:
    for lv in LEVELS:
        d=paired(filtered,lv,kind)
        summary.append({'Measure':kind,'Level':lv,'Male':d['Male'].mean(),'Female':d['Female'].mean(),'Count':len(d)})
s=pd.DataFrame(summary)
fig=make_subplots(rows=1,cols=2,subplot_titles=['Completion rates','Out-of-school rates'],horizontal_spacing=.15)
for j,kind in enumerate(['completion','oosr'],start=1):
    d=s[s['Measure']==kind]
    for g,color in [('Male',MALE),('Female',FEMALE)]:
        fig.add_trace(go.Bar(x=d['Level'],y=d[g],name=g,marker_color=color,legendgroup=g,showlegend=j==1,customdata=d['Count'],hovertemplate='%{x}<br>%{y:.1f}%<br>Countries with both values: %{customdata}<extra></extra>'),row=1,col=j)
    fig.update_yaxes(title_text='Average rate (%)',rangemode='tozero',row=1,col=j)
fig.update_layout(barmode='group',title='Gender Comparison Across Education Levels',height=450)
show(fig,'q2bar')
d=paired(filtered,level,'completion')
if not d.empty:
    d=d.assign(AbsGap=lambda x:x['Gap'].abs()).nlargest(8,'AbsGap').sort_values('AbsGap',ascending=False)
    fig=go.Figure()
    for _,r in d.iterrows():
        fig.add_trace(go.Scatter(x=[r['Male'],r['Female']],y=[r['Country']]*2,mode='lines',line=dict(color='#B5BCC5',width=3),showlegend=False,hoverinfo='skip'))
    for g,color in [('Male',MALE),('Female',FEMALE)]:
        fig.add_trace(go.Scatter(x=d[g],y=d['Country'],mode='markers',name=g,marker=dict(size=11,color=color),customdata=d['Gap'],hovertemplate='%{y}<br>'+g+': %{x:.1f}%<br>Female − male: %{customdata:+.1f} pp<extra></extra>'))
    fig.update_layout(title=f'Largest Gender Gaps — {level} Completion',xaxis_title='Completion rate (%)',yaxis=dict(autorange='reversed'),height=max(400,100+43*len(d)))
    show(fig,'q2dumbbell')
else: st.warning('No paired reported values for the gender-gap chart.')

st.subheader('Q3 — Completion Rates Across Education Levels')
st.caption('Country-level averages of available male/female rates, by education level. Education-level filter is not applied here so all three levels remain comparable.')
frames=[]
for lv,k in LEVELS.items():
    c=[f'Completion_Rate_{k}_{g}' for g in selected]
    d=pd.DataFrame({'Country':filtered[COUNTRY],'Education Level':lv,'Completion Rate (%)':pd.concat([reported(filtered,x) for x in c],axis=1).mean(axis=1)})
    frames.append(d)
boxdata=pd.concat(frames).dropna(subset=['Completion Rate (%)'])
if not boxdata.empty:
    fig=px.box(boxdata,x='Education Level',y='Completion Rate (%)',color='Education Level',points='outliers',category_orders={'Education Level':list(LEVELS)},title=f'Completion Rate Distribution ({gender})',hover_data=['Country'])
    fig.update_layout(showlegend=False)
    show(fig,'q3box')
else: st.warning('No reported completion rates for this selection.')

st.subheader('Q4 — Birth Rate & Female Primary Completion')
st.caption('Phase 1 methodology: zero/missing values in each variable are replaced with the full-dataset nonzero mean. Country filter applies; gender and level filters do not change this female-primary analysis.')

# Impute on the full dataset BEFORE filtering, to keep the reference means consistent.
q4cols = ['Birth_Rate', 'Completion_Rate_Primary_Female']
q4all = df[[COUNTRY] + q4cols].copy()
for c in q4cols:
    original = pd.to_numeric(q4all[c], errors='coerce')
    missing = original.isna() | original.eq(0)
    nonzero = original.mask(missing)
    q4all[c + '_imputed_here'] = missing
    q4all[c] = nonzero.fillna(nonzero.mean())
q4 = q4all[q4all[COUNTRY].isin(countries)].copy() if countries else q4all.copy()
q4 = q4.dropna(subset=q4cols)
q4['Value type'] = np.where(q4[[c + '_imputed_here' for c in q4cols]].any(axis=1), 'Mean-imputed in dashboard', 'Nonzero values in workbook')
if len(q4) >= 2:
    fig = go.Figure()
    for label, color, symbol in [('Nonzero values in workbook', '#4682B4', 'circle'), ('Mean-imputed in dashboard', '#E17A37', 'circle-open')]:
        subset = q4[q4['Value type'] == label]
        if not subset.empty:
            fig.add_trace(go.Scatter(x=subset['Birth_Rate'], y=subset['Completion_Rate_Primary_Female'], mode='markers', name=label, marker=dict(color=color, symbol=symbol, size=9, line=dict(width=1.5)), text=subset[COUNTRY], customdata=np.column_stack((subset['Birth_Rate_imputed_here'], subset['Completion_Rate_Primary_Female_imputed_here'])), hovertemplate='%{text}<br>Birth rate: %{x:.2f}<br>Female primary completion: %{y:.1f}%<br>Birth rate replaced: %{customdata[0]}<br>Completion replaced: %{customdata[1]}<extra></extra>'))
    if q4['Birth_Rate'].nunique() > 1:
        slope, intercept = np.polyfit(q4['Birth_Rate'], q4['Completion_Rate_Primary_Female'], 1)
        xs = np.linspace(q4['Birth_Rate'].min(), q4['Birth_Rate'].max(), 100)
        fig.add_trace(go.Scatter(x=xs, y=slope*xs+intercept, mode='lines', name='Linear trend', line=dict(color='#C23B3B', width=2)))
    fig.update_layout(title='Birth Rate vs Female Primary Completion Rate (Mean Imputation)', xaxis_title='Birth rate', yaxis_title='Female primary completion (%)')
    show(fig, 'q4scatter')
    corr = q4['Birth_Rate'].corr(q4['Completion_Rate_Primary_Female'])
    st.caption(f'Pearson correlation: {corr:.2f} | Countries: {len(q4)} | Points imputed in this dashboard: {(q4["Value type"] == "Mean-imputed in dashboard").sum()}. Correlation does not establish causation.')
    st.caption('The open markers identify rows where this dashboard replaced zero/missing values. The workbook has no independent imputation flag, so these should not be described as verified original reported/imputed classifications.')
else:
    st.warning('Select at least two countries with available values to display the relationship.')

with st.expander('Data Preview and Methodology'):
    st.dataframe(filtered,width='stretch')
    st.write('The dataset has no time variable; comparisons are cross-sectional, not trends over time. Q1–Q3 and educational KPIs exclude zero-valued indicators. Q4 applies column-mean imputation to zero/missing birth-rate and female-primary-completion values using full-dataset means before country filtering. Open markers indicate replacements performed by this app; no original imputation mask is provided. The methods therefore differ intentionally between research questions, matching the reported-only versus imputed analyses in the report.')
