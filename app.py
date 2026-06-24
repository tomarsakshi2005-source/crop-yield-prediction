from flask import Flask, render_template, request, jsonify
import pandas as pd
import pickle

app = Flask(__name__)

# Load your asset data once when the server starts
with open('crop_knowledge_final_v10.pkl', 'rb') as f:
    kb = pickle.load(f)

@app.route('/')
def home():
    # Pass initial data to populate dropdowns
    return render_template('index.html', 
                           states=kb['all_states'], 
                           months=['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'])

@app.route('/get_regions', methods=['POST'])
def get_regions():
    state = request.json.get('state')
    regions = sorted(kb['state_dist_map'].get(state, []))
    return jsonify({'regions': regions})

@app.route('/get_analysis', methods=['POST'])
def get_analysis():
    data = request.json
    state = data.get('state')
    region = data.get('region')
    month = data.get('month')
    
    # Seasonal logic
    current_season = 'Kharif' if month in ['JUN', 'JUL', 'AUG', 'SEP', 'OCT'] else 'Rabi' if month in ['NOV', 'DEC', 'JAN', 'FEB'] else 'Zaid'
    
    # Process Crop Tables
    yield_data = kb['dist_yield_rank'].get((state, region), {})
    best_5, worst_5, top_crop_name = [], [], None
    
    if yield_data:
        s = pd.Series(yield_data)
        s.index = [i.replace(' YIELD (Kg per ha)', '').strip() for i in s.index]
        
        seasonal_list = kb['seasons'][current_season]
        filtered = s[s.index.isin(seasonal_list)]
        if filtered.empty: filtered = s[s > 0]
        
        b5 = filtered.sort_values(ascending=False).head(5)
        w5 = filtered.sort_values(ascending=True).head(5)
        
        if not b5.empty:
            top_crop_name = b5.index[0]
            
        best_5 = [{"crop": k, "yield": int(v)} for k, v in b5.items()]
        worst_5 = [{"crop": k, "yield": int(v)} for k, v in w5.items()]

    # Fetch Technical Data for Smart Default Crop
    tech_info = None
    all_tech_crops = sorted([c.title() for c in kb['tech_data'].keys()])
    
    if top_crop_name:
        mapped_name = kb['tech_mapping'].get(top_crop_name.lower(), top_crop_name.lower())
        tech_info = kb['tech_data'].get(mapped_name.lower())

    return jsonify({
        'season': current_season,
        'best_5': best_5,
        'worst_5': worst_5,
        'all_tech_crops': all_tech_crops,
        'tech_info': tech_info
    })

if __name__ == '__main__':
    app.run(debug=True)
    