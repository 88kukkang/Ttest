"""
data/q33-subfertility/build.py
Reads raw public datasets and produces q33_data.json:
- 15143044.xlsx: 국민건강보험공단 불임 및 유산 관련 상병별 진료현황 (2010~2023)
- 15127567.csv: 국민건강보험공단 특정기호 F021 난임진료의 시도별 연령별 진료인원 및 건수 (2018~2022)
- 15125614.csv: 국민건강보험공단 연도별 난임시술 현황 (2018~2022)
- 15127541.csv: 국민건강보험공단 연령별 요양기관종별 난임시술 진료건수 (2018~2022)
- DT_1B8000F from data/q32-marriage/kosis_raw.json (출생아수 2010~2023)
"""
import openpyxl
import csv
import json
import os
import sys
from collections import defaultdict

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    out_json = os.path.join(base_dir, 'q33_data.json')
    
    # 1. KOSIS Birth numbers (2010~2023)
    kosis_path = os.path.join(base_dir, '..', 'q32-marriage', 'kosis_raw.json')
    birth_dict = {}
    if os.path.exists(kosis_path):
        with open(kosis_path, 'r', encoding='utf-8') as f:
            kd = json.load(f)
            f_raw = kd.get('DT_1B8000F', {})
            yrs = f_raw.get('yrs', [])
            items = f_raw.get('items', {})
            # first item is birth count
            b_key = list(items.keys())[0]
            b_vals = items[b_key]
            for y, b in zip(yrs, b_vals):
                if 2010 <= y <= 2023:
                    birth_dict[y] = b
    print(f'Birth numbers loaded for {len(birth_dict)} years: {sorted(birth_dict.keys())}')
    
    # 2. 15143044.xlsx: N46 (Male infertility), N97 (Female infertility) 2010~2023
    xlsx_path = os.path.join(base_dir, '15143044.xlsx')
    if not os.path.exists(xlsx_path):
        xlsx_path = os.path.join(base_dir, '15143044.csv')
    
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    ws1 = wb['1. 특정 주상병코드(N46, N97) 진료현황']
    
    # Headers: 진료년도, 요양기관주소지, 연령, 성별, 요양기관종별, 진료형태, 진료인원(명)
    rows1 = ws1.iter_rows(values_only=True)
    next(rows1)
    
    # Group by year: total, male, female, age brackets
    # Age brackets for pots: '24세 이하', '25–29세', '30–34세', '35–39세', '40–44세', '45세 이상'
    POT_TIERS = ['24세 이하', '25–29세', '30–34세', '35–39세', '40–44세', '45세 이상']
    
    yearly_infertility = {}
    years_14 = range(2010, 2024)
    for y in years_14:
        yearly_infertility[y] = {
            'tot': 0, 'male': 0, 'female': 0,
            'tiers': {t: {'tot': 0, 'm': 0, 'w': 0} for t in POT_TIERS},
            'single_ages': defaultdict(int)
        }
    
    for r in rows1:
        y = r[0]
        if y is None or y not in yearly_infertility: continue
        age_str = str(r[2]).strip()
        gender = str(r[3]).strip()
        val = r[6]
        cnt = int(val) if isinstance(val, (int, float)) else (int(val) if str(val).isdigit() else 1)
        
        yearly_infertility[y]['tot'] += cnt
        if gender == '남자':
            yearly_infertility[y]['male'] += cnt
            gkey = 'm'
        else:
            yearly_infertility[y]['female'] += cnt
            gkey = 'w'
        
        if '미만' in age_str:
            t = '24세 이하'
            yearly_infertility[y]['single_ages'][19] += cnt
        elif '이상' in age_str:
            t = '45세 이상'
            yearly_infertility[y]['single_ages'][50] += cnt
        else:
            try:
                a = int(age_str.replace('세', ''))
                yearly_infertility[y]['single_ages'][a] += cnt
                if a <= 24: t = '24세 이하'
                elif a <= 29: t = '25–29세'
                elif a <= 34: t = '30–34세'
                elif a <= 39: t = '35–39세'
                elif a <= 44: t = '40–44세'
                else: t = '45세 이상'
            except:
                t = '45세 이상'
        
        yearly_infertility[y]['tiers'][t]['tot'] += cnt
        yearly_infertility[y]['tiers'][t][gkey] += cnt
    
    print('15143044 sheet 1 aggregation complete.')
    for y in [2010, 2015, 2020, 2023]:
        d = yearly_infertility[y]
        print(f"  {y}년: 총 {d['tot']:,}명 (남 {d['male']:,}명, 여 {d['female']:,}명)")
    
    # Sheet 2: Miscarriage (O03-O06)
    ws2 = wb['2. 특정 주상병코드(O03-O06) 진료현황']
    rows2 = ws2.iter_rows(values_only=True)
    next(rows2)
    yearly_miscarriage = defaultdict(int)
    for r in rows2:
        y = r[0]
        if y is None or y not in years_14: continue
        val = r[5]
        cnt = int(val) if isinstance(val, (int, float)) else (int(val) if str(val).isdigit() else 1)
        yearly_miscarriage[y] += cnt
    print('15143044 sheet 2 aggregation complete.')
    
    # 3. 15127567.csv: F021 (난임시술 건강보험 산정특례) 2018~2022
    f021_path = os.path.join(base_dir, '15127567.csv')
    f021_years = [2018, 2019, 2020, 2021, 2022]
    f021_sido = defaultdict(lambda: defaultdict(lambda: {'patients': 0, 'cases': 0}))
    f021_age = defaultdict(lambda: defaultdict(lambda: {'patients': 0, 'cases': 0}))
    f021_tot = defaultdict(lambda: {'patients': 0, 'cases': 0})
    
    F021_TIERS = ['29세 이하', '30–34세', '35–39세', '40–44세', '45세 이상']
    
    with open(f021_path, 'r', encoding='cp949') as f:
        r = csv.DictReader(f)
        for row in r:
            y = int(row['진료연도'].replace('년', ''))
            sido = row['주소지'].strip().replace('제주도', '제주특별자치도')
            age = int(row['연령'].replace('세', ''))
            p = int(row['진료인원(명)'])
            c = int(row['진료건수(건)'])
            
            f021_tot[y]['patients'] += p
            f021_tot[y]['cases'] += c
            f021_sido[y][sido]['patients'] += p
            f021_sido[y][sido]['cases'] += c
            
            if age <= 29: t = '29세 이하'
            elif age <= 34: t = '30–34세'
            elif age <= 39: t = '35–39세'
            elif age <= 44: t = '40–44세'
            else: t = '45세 이상'
            
            f021_age[y][t]['patients'] += p
            f021_age[y][t]['cases'] += c
    
    print('15127567 aggregation complete.')
    for y in f021_years:
        print(f"  F021 {y}년: {f021_tot[y]['patients']:,}명, {f021_tot[y]['cases']:,}건")
    
    # 4. 15127541.csv: 시술구분별 체외수정 vs 정자주입술 2018~2022
    p_path = os.path.join(base_dir, '15127541.csv')
    proc_data = defaultdict(lambda: {'ivf': 0, 'iui': 0, 'ivf_age': defaultdict(int), 'iui_age': defaultdict(int), 'hosp': defaultdict(int)})
    with open(p_path, 'r', encoding='cp949') as f:
        r = csv.DictReader(f)
        for row in r:
            y = int(row['진료년도'].replace('년', ''))
            stype = row['시술구분'].strip() # 체외수정, 정자주입술
            age = int(row['연령'].replace('세', ''))
            hosp = row['요양기관종별'].strip()
            c = int(row['진료건수(건)'])
            
            if age <= 29: t = '29세 이하'
            elif age <= 34: t = '30–34세'
            elif age <= 39: t = '35–39세'
            elif age <= 44: t = '40–44세'
            else: t = '45세 이상'
            
            if stype == '체외수정':
                proc_data[y]['ivf'] += c
                proc_data[y]['ivf_age'][t] += c
            else:
                proc_data[y]['iui'] += c
                proc_data[y]['iui_age'][t] += c
            proc_data[y]['hosp'][hosp] += c
    
    print('15127541 aggregation complete.')
    
    # Assemble final structured payload
    payload = {
        'pots': {
            'yrs': list(years_14),
            'tiers': POT_TIERS,
            'tot': [yearly_infertility[y]['tot'] for y in years_14],
            'male': [yearly_infertility[y]['male'] for y in years_14],
            'female': [yearly_infertility[y]['female'] for y in years_14],
            'male_pct': [round(yearly_infertility[y]['male'] / yearly_infertility[y]['tot'] * 100, 1) for y in years_14],
            'by_tier': {
                t: {
                    'tot': [yearly_infertility[y]['tiers'][t]['tot'] for y in years_14],
                    'm': [yearly_infertility[y]['tiers'][t]['m'] for y in years_14],
                    'w': [yearly_infertility[y]['tiers'][t]['w'] for y in years_14],
                } for t in POT_TIERS
            },
            'births': [birth_dict.get(y, 0) for y in years_14],
            'ratio_to_birth': [round(yearly_infertility[y]['tot'] / birth_dict.get(y, 1) * 100, 1) for y in years_14],
            'ratio_female_to_birth': [round(yearly_infertility[y]['female'] / birth_dict.get(y, 1) * 100, 1) for y in years_14],
            'miscarriages': [yearly_miscarriage[y] for y in years_14]
        },
        'f021': {
            'yrs': f021_years,
            'tiers': F021_TIERS,
            'patients': [f021_tot[y]['patients'] for y in f021_years],
            'cases': [f021_tot[y]['cases'] for y in f021_years],
            'per_person': [round(f021_tot[y]['cases'] / f021_tot[y]['patients'], 2) for y in f021_years],
            'by_tier': {
                t: {
                    'patients': [f021_age[y][t]['patients'] for y in f021_years],
                    'cases': [f021_age[y][t]['cases'] for y in f021_years]
                } for t in F021_TIERS
            },
            'over40_pct': [
                round((f021_age[y]['40–44세']['patients'] + f021_age[y]['45세 이상']['patients']) / f021_tot[y]['patients'] * 100, 1)
                for y in f021_years
            ]
        },
        'sido': {
            'names': sorted(f021_sido[2022].keys()),
            'data22': {
                s: {
                    'p18': f021_sido[2018][s]['patients'],
                    'c18': f021_sido[2018][s]['cases'],
                    'p22': f021_sido[2022][s]['patients'],
                    'c22': f021_sido[2022][s]['cases'],
                    'chg_pct': round((f021_sido[2022][s]['patients'] / f021_sido[2018][s]['patients'] - 1) * 100, 1) if f021_sido[2018][s]['patients'] else 0.0
                } for s in f021_sido[2022]
            }
        },
        'procedures': {
            'yrs': f021_years,
            'ivf': [proc_data[y]['ivf'] for y in f021_years],
            'iui': [proc_data[y]['iui'] for y in f021_years],
            'ivf_pct': [round(proc_data[y]['ivf'] / (proc_data[y]['ivf'] + proc_data[y]['iui']) * 100, 1) for y in f021_years],
            'iui_pct': [round(proc_data[y]['iui'] / (proc_data[y]['ivf'] + proc_data[y]['iui']) * 100, 1) for y in f021_years],
            'age22': {
                'ivf': {t: proc_data[2022]['ivf_age'][t] for t in F021_TIERS},
                'iui': {t: proc_data[2022]['iui_age'][t] for t in F021_TIERS}
            },
            'hosp22': dict(proc_data[2022]['hosp'])
        }
    }
    
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'Wrote {out_json} ({os.path.getsize(out_json):,} bytes)')

if __name__ == '__main__':
    main()
