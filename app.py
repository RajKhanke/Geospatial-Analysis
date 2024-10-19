from flask import Flask, render_template, request
import folium
from folium.plugins import HeatMapWithTime, FeatureGroupSubGroup, HeatMap
import pandas as pd
import os

app = Flask(__name__)


url='https://drive.google.com/file/d/1_vd4HISZB2h2--CiXKezeWDXHHo2fY23/view?usp=sharing'
df = pd.read_csv('https://drive.usercontent.google.com/download?id={}&export=download&authuser=0&confirm=t'.format(url.split('/')[-2]))
df.columns = ['State', 'District', 'Crop_Year', 'Season', 'Crop', 'Area', 'Production', 'Latitude', 'Longitude']


@app.route('/')
def home():
    return render_template('index.html', map_html="", selected_map="Home")


@app.route('/prodction_analysis', methods=['GET', 'POST'])
def production_analysis():
    crop_options = df['Crop'].unique().tolist()
    selected_crop = request.form.get('crop_type') if request.method == 'POST' else None

    if not selected_crop:
        return render_template('index.html', map_html="", selected_map="Production Analysis",
                               crop_options=crop_options, selected_crop=None)

    crop_data = df[df['Crop'] == selected_crop]

    if crop_data.empty:
        return render_template('index.html', map_html="", selected_map="No Data Available",
                               crop_options=crop_options, selected_crop=selected_crop)

    time_index = crop_data['Crop_Year'].unique()
    heatmap_data = [
        [[row['Latitude'], row['Longitude']] for _, row in crop_data[crop_data['Crop_Year'] == year].iterrows()]
        for year in time_index
    ]

    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
    heatmap = HeatMapWithTime(
        heatmap_data,
        index=[str(year) for year in time_index],
        auto_play=True,
        max_opacity=0.6
    )
    heatmap.add_to(m)

    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html, selected_map="Production Heatmap Analysis",
                           crop_options=crop_options, selected_crop=selected_crop)


@app.route('/heatmap_analysis')
def heatmap_analysis():
    global df  # Declare df as global
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)
    fg = folium.FeatureGroup(name="Crops")
    m.add_child(fg)
    df_sampled = df.sample(frac=0.005, random_state=42)  # Use a different variable for sampled df
    for crop in df_sampled['Crop'].unique():
        subgroup = FeatureGroupSubGroup(fg, crop)
        m.add_child(subgroup)
        crop_data = df_sampled[df_sampled['Crop'] == crop]

        heatmap_data = [[row['Latitude'], row['Longitude']] for _, row in crop_data.iterrows()]
        HeatMap(heatmap_data).add_to(subgroup)

    folium.LayerControl(collapsed=False).add_to(m)

    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html, selected_map="Crop Heatmap Analysis")


@app.route('/season_analysis')
def season_analysis():
    global df  # Declare df as global

    # Initialize the map centered over India with an appropriate zoom level
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)

    # Sample a fraction of the dataframe for performance
    df_sampled = df.sample(frac=0.005, random_state=42)

    # Create a dictionary to store top 5 crops for each location
    top_crops = {}

    # Collect the top crops for each unique location (Latitude, Longitude)
    for _, row in df_sampled.iterrows():
        lat_lon = (row['Latitude'], row['Longitude'])
        crop = row['Crop']
        production = row['Production']

        if lat_lon not in top_crops:
            top_crops[lat_lon] = {'Season': row['Season'], 'Crops': {}, 'Area': row['Area']}

        if crop not in top_crops[lat_lon]['Crops']:
            top_crops[lat_lon]['Crops'][crop] = 0
        top_crops[lat_lon]['Crops'][crop] += production

    # Limit to top 5 crops for each location
    for location, data in top_crops.items():
        top_crops[location]['Crops'] = sorted(data['Crops'].items(), key=lambda x: x[1], reverse=True)[:5]

    # Add scatter points for each unique location with a different color for each season
    season_colors = {
        'Kharif': 'orange',
        'Rabi': 'green',
        'Winter': 'blue',
        'Autumn':'pink',
        'Rabi':'brown',
        'Summer':'yellow',
        'Whole Year':'Red'
    }

    for (latitude, longitude), data in top_crops.items():
        season = data['Season']
        top_crop_list = data['Crops']
        area = data['Area']

        # Create a string for the top crops
        top_crops_str = "<br>".join([f"{crop[0]}: {crop[1]}" for crop in top_crop_list])

        # Add a scatter point to the map for each location
        folium.CircleMarker(
            location=[latitude, longitude],
            radius=7,  # Fixed radius for scatter points
            color=season_colors.get(season, 'gray'),  # Use season color or gray if not found
            fill=True,
            fill_color=season_colors.get(season, 'gray'),
            fill_opacity=0.7,
            tooltip=(f"Latitude: {latitude}<br>"
                     f"Longitude: {longitude}<br>"
                     f"Season: {season}<br>"
                     f"Area: {area}<br>"
                     f"Top 5 Crops:<br>{top_crops_str}")
        ).add_to(m)

    # Convert the map to HTML format for rendering
    map_html = m._repr_html_()

    # Render the map in the template
    return render_template('index.html', map_html=map_html, selected_map="Season Analysis")


@app.route('/crop_analysis')
def crop_analysis():
    global df  # Declare df as global
    df_sampled = df.sample(frac=0.005, random_state=42)  # Use a different variable for sampled df
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)

    for district in df_sampled['District'].unique():
        district_data = df_sampled[df_sampled['District'] == district]
        top_crops = district_data.groupby('Crop')['Production'].sum().nlargest(5).index.tolist()
        lat, lon = district_data.iloc[0]['Latitude'], district_data.iloc[0]['Longitude']

        folium.Marker(
            location=[lat, lon],
            popup=f"<b>District:</b> {district}<br><b>Top 5 Crops:</b> {', '.join(top_crops)}",
            icon=folium.Icon(icon='arrow-up', color='green')
        ).add_to(m)

    map_html = m._repr_html_()
    return render_template('index.html', map_html=map_html, selected_map="District Crop Analysis")


@app.route('/combined_analysis')
def combined_analysis():
    global df  # Declare df as global

    # Sample a fraction of the dataframe for performance
    df_sampled = df.sample(frac=0.005, random_state=42)

    # Create the map centered over India with an appropriate zoom level
    m = folium.Map(location=[20.5937, 78.9629], zoom_start=5)

    # Prepare heatmap data for area
    area_heat_data = [
        [row['Latitude'], row['Longitude'], row['Area']]
        for _, row in df_sampled.iterrows()
    ]

    # Add the heatmap for area (blue to red: low to high)
    HeatMap(
        data=area_heat_data,
        min_opacity=0.3,
        max_opacity=0.8,
        radius=15,
        blur=10,
        gradient={0.0: 'blue', 0.5: 'lightblue', 1.0: 'red'}
    ).add_to(m)

    # Prepare heatmap data for production
    production_heat_data = [
        [row['Latitude'], row['Longitude'], row['Production']]
        for _, row in df_sampled.iterrows()
    ]

    # Add the heatmap for production (green to red: low to high production)
    HeatMap(
        data=production_heat_data,
        min_opacity=0.3,
        max_opacity=0.8,
        radius=15,
        blur=10,
        gradient={0.0: 'green', 0.5: 'yellow', 1.0: 'red'}
    ).add_to(m)

    # Scatter plot for different seasons with distinct colors
    season_colors = {
        'Kharif': 'purple',
        'Rabi': 'orange',
        'Rabi': 'cyan',
        'Winter':'Yellow',
        'Summer':'Green',
        'Whole Year':'Red'
    }

    for _, row in df_sampled.iterrows():
        season = row['Season']
        color = season_colors.get(season, 'gray')  # Default to gray if the season is not recognized
        folium.CircleMarker(
            location=[row['Latitude'], row['Longitude']],
            radius=5,
            color=color,
            fill=True,
            fill_opacity=0.7,
            tooltip=(f"District: {row['District']}<br>"
                     f"Season: {row['Season']}<br>"
                     f"Area: {row['Area']}<br>"
                     f"Production: {row['Production']}")
        ).add_to(m)

    # Convert the map to HTML format
    map_html = m._repr_html_()

    # Render the map in the template
    return render_template('index.html', map_html=map_html, selected_map="Combined Area & Production Heatmaps")

if __name__ == '__main__':
    app.run(debug=True)
