import requests
from typing import Tuple, Optional, List
import time
import logging
from math import cos, radians, sin, sqrt, atan2

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_URL = "https://nominatim.openstreetmap.org"
HEADERS = {
    "User-Agent": "DMS-Disaster-Management-System/1.0"
}

def geocode_address(address: str, max_retries: int = 3) -> Optional[Tuple[float, float]]:
    """
    Convert a human-readable address into latitude & longitude using OpenStreetMap.
    """
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/search"
            params = {
                "q": address, 
                "format": "json",
                "addressdetails": 1,
                "limit": 1
            }
            
            response = requests.get(url, params=params, headers=HEADERS, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if data:
                lat = float(data[0]["lat"])
                lon = float(data[0]["lon"])
                logger.info(f"Geocoded address: {address} -> ({lat}, {lon})")
                return lat, lon
            
            logger.warning(f"No results found for address: {address}")
            return None, None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Geocoding timed out for address: {address}. Attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(2)
            continue
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Geocoding request error: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
            
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Error parsing geocoding response: {e}")
            return None, None
            
        except Exception as e:
            logger.error(f"Unexpected error during geocoding: {e}")
            return None, None
    
    logger.error(f"Failed to geocode address after {max_retries} attempts: {address}")
    return None, None

def reverse_geocode(lat: float, lon: float, max_retries: int = 2) -> Optional[str]:
    """
    Convert latitude & longitude back into a human-readable address.
    """
    for attempt in range(max_retries):
        try:
            url = f"{BASE_URL}/reverse"
            params = {
                "lat": lat, 
                "lon": lon, 
                "format": "json",
                "addressdetails": 1,
                "zoom": 18
            }
            
            response = requests.get(url, params=params, headers=HEADERS, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "display_name" in data:
                address = data["display_name"]
                logger.info(f"Reverse geocoded: ({lat}, {lon}) -> {address}")
                return address
            
            return None
            
        except requests.exceptions.Timeout:
            logger.warning(f"Reverse geocoding timed out. Attempt {attempt + 1}/{max_retries}")
            if attempt < max_retries - 1:
                time.sleep(1)
            continue
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Reverse geocoding request error: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Unexpected error during reverse geocoding: {e}")
            return None
    
    return None

def distance_km(point_a: Tuple[float, float], point_b: Tuple[float, float]) -> float:
    """
    Calculate distance between two points in kilometers using Haversine formula
    """
    try:
        # Haversine formula
        lat1, lon1 = radians(point_a[0]), radians(point_a[1])
        lat2, lon2 = radians(point_b[0]), radians(point_b[1])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1 - a))
        
        # Earth radius in kilometers
        R = 6371.0
        distance = R * c
        
        return distance
        
    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        return float('inf')