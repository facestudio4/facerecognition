import folium

# coordinates (Mumbai example)
m = folium.Map(location=[19.0760, 72.8777], zoom_start=10)

# add marker
folium.Marker(
    [19.0760, 72.8777],
    popup="Mumbai",
    tooltip="Click here"
).add_to(m)

# save map
m.save("map.html")  