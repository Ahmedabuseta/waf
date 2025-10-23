from site_management.utils.ip_utils import geolocate_ip

geo_data = geolocate_ip("197.43.188.212")
print(geo_data)
