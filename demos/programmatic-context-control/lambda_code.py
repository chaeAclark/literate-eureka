import json
import random

from datetime import datetime, timedelta
from typing import List, Dict, Any


def lambda_handler(event, context):
    tool_name = context.client_context.custom.get('bedrockAgentCoreToolName')
    tool_name = tool_name.split('___')[-1]

    # Internal/Controlled travel tools
    if tool_name == 'get_my_bookings__controlled':
        return get_my_bookings__controlled(**event)
    elif tool_name == 'get_loyalty_status__controlled':
        return get_loyalty_status__controlled(**event)
    elif tool_name == 'get_saved_travelers__controlled':
        return get_saved_travelers__controlled(**event)
    elif tool_name == 'get_travel_preferences__controlled':
        return get_travel_preferences__controlled(**event)
    elif tool_name == 'get_past_trips__controlled':
        return get_past_trips__controlled(**event)
    elif tool_name == 'get_saved_payment_methods__controlled':
        return get_saved_payment_methods__controlled(**event)
    elif tool_name == 'get_travel_credits__controlled':
        return get_travel_credits__controlled(**event)
    elif tool_name == 'get_upcoming_trips__controlled':
        return get_upcoming_trips__controlled(**event)
    elif tool_name == 'update_traveler_profile__controlled':
        return update_traveler_profile__controlled(**event)
    elif tool_name == 'request_travel_approval__controlled':
        return request_travel_approval__controlled(**event)
    
    # Public travel tools
    elif tool_name == 'search_flights__public':
        return search_flights__public(**event)
    elif tool_name == 'search_hotels__public':
        return search_hotels__public(**event)
    elif tool_name == 'search_car_rentals__public':
        return search_car_rentals__public(**event)
    elif tool_name == 'get_airport_info__public':
        return get_airport_info__public(**event)
    elif tool_name == 'check_visa_requirements__public':
        return check_visa_requirements__public(**event)
    elif tool_name == 'get_destination_weather__public':
        return get_destination_weather__public(**event)
    elif tool_name == 'get_currency_exchange__public':
        return get_currency_exchange__public(**event)
    elif tool_name == 'find_attractions__public':
        return find_attractions__public(**event)
    elif tool_name == 'search_restaurants__public':
        return search_restaurants__public(**event)
    elif tool_name == 'get_travel_alerts__public':
        return get_travel_alerts__public(**event)
    elif tool_name == 'calculate_trip_cost__public':
        return calculate_trip_cost__public(**event)
    elif tool_name == 'get_local_transportation__public':
        return get_local_transportation__public(**event)
    elif tool_name == 'find_travel_insurance__public':
        return find_travel_insurance__public(**event)
    elif tool_name == 'get_packing_checklist__public':
        return get_packing_checklist__public(**event)
    
    # Tool not found
    return {
        'statusCode': 400,
        'body': json.dumps({
            'error': f'The tool name "{tool_name}" was not available in the Lambda function.',
        })
    }


# ============================================================================
# CONTROLLED/INTERNAL TOOLS - User-specific travel data
# ============================================================================

def get_my_bookings__controlled(status: str = "all") -> List[Dict[str, Any]]:
    """Get user's travel bookings from their account."""
    bookings = [
        {
            "booking_id": "BK789456",
            "type": "flight",
            "status": "confirmed",
            "confirmation": "ABC123",
            "airline": "United Airlines",
            "flight_number": "UA1234",
            "route": "SFO -> JFK",
            "departure": "2024-02-15T08:00:00",
            "arrival": "2024-02-15T16:30:00",
            "seat": "12A",
            "class": "Economy Plus",
            "price": 456.80
        },
        {
            "booking_id": "BK789457",
            "type": "hotel",
            "status": "confirmed",
            "confirmation": "HTL987654",
            "hotel_name": "Marriott Marquis Times Square",
            "check_in": "2024-02-15",
            "check_out": "2024-02-18",
            "room_type": "Deluxe King",
            "nights": 3,
            "price": 899.97
        },
        {
            "booking_id": "BK789458",
            "type": "car_rental",
            "status": "pending",
            "confirmation": "CAR456789",
            "company": "Hertz",
            "pickup_location": "JFK Airport",
            "pickup_date": "2024-02-15T17:00:00",
            "dropoff_date": "2024-02-18T10:00:00",
            "car_type": "Intermediate SUV",
            "price": 234.50
        }
    ]
    
    if status != "all":
        bookings = [b for b in bookings if b["status"] == status]
    
    return {
        "bookings": bookings,
        "total_count": len(bookings),
        "total_value": sum(b.get("price", 0) for b in bookings)
    }


def get_loyalty_status__controlled() -> Dict[str, Any]:
    """Get user's loyalty program status across different travel providers."""
    return {
        "programs": [
            {
                "provider": "United Airlines",
                "program": "MileagePlus",
                "member_number": "MP12345678",
                "tier": "Silver",
                "miles": 45320,
                "miles_to_next_tier": 14680,
                "next_tier": "Gold",
                "companion_passes": 0,
                "upgrade_certificates": 2
            },
            {
                "provider": "Marriott",
                "program": "Bonvoy",
                "member_number": "MB87654321",
                "tier": "Gold Elite",
                "points": 128450,
                "free_night_awards": 1,
                "elite_night_credits": 42,
                "nights_to_next_tier": 8,
                "next_tier": "Platinum Elite"
            },
            {
                "provider": "Hertz",
                "program": "Gold Plus Rewards",
                "member_number": "HZ9876543",
                "tier": "Five Star",
                "points": 3420,
                "free_rental_days": 1
            }
        ],
        "credit_cards": [
            {
                "name": "Chase Sapphire Reserve",
                "points": 95000,
                "value_estimate": 1425.00,
                "annual_travel_credit": 300,
                "used_this_year": 150
            }
        ]
    }


def get_saved_travelers__controlled() -> List[Dict[str, Any]]:
    """Get saved traveler profiles for quick booking."""
    return {
        "travelers": [
            {
                "id": "traveler_001",
                "type": "primary",
                "first_name": "John",
                "last_name": "Smith",
                "date_of_birth": "1985-06-15",
                "passport_number": "US1234567",
                "passport_expiry": "2028-06-15",
                "nationality": "United States",
                "known_traveler_number": "KTN12345678",
                "global_entry": True,
                "email": "john.smith@email.com",
                "phone": "+1-555-0123"
            },
            {
                "id": "traveler_002",
                "type": "companion",
                "first_name": "Jane",
                "last_name": "Smith",
                "date_of_birth": "1987-03-22",
                "passport_number": "US7654321",
                "passport_expiry": "2027-03-22",
                "nationality": "United States",
                "email": "jane.smith@email.com",
                "phone": "+1-555-0124"
            }
        ]
    }


def get_travel_preferences__controlled() -> Dict[str, Any]:
    """Get user's saved travel preferences."""
    return {
        "flight_preferences": {
            "preferred_airlines": ["United Airlines", "Delta"],
            "seat_preference": "aisle",
            "cabin_class": "economy_plus",
            "meal_preference": "vegetarian",
            "special_assistance": None
        },
        "hotel_preferences": {
            "preferred_chains": ["Marriott", "Hilton", "Hyatt"],
            "room_type": "king_bed",
            "floor_preference": "high",
            "smoking": False,
            "amenities": ["wifi", "gym", "breakfast"]
        },
        "car_rental_preferences": {
            "preferred_companies": ["Hertz", "Enterprise"],
            "car_size": "intermediate_suv",
            "transmission": "automatic",
            "insurance": "full_coverage"
        },
        "general": {
            "home_airport": "SFO",
            "currency": "USD",
            "language": "en-US",
            "notifications": {
                "email": True,
                "sms": True,
                "app_push": True
            }
        }
    }


def get_past_trips__controlled(limit: int = 5) -> List[Dict[str, Any]]:
    """Get user's travel history."""
    trips = [
        {
            "trip_id": "TRIP2023_089",
            "destination": "Tokyo, Japan",
            "dates": "2023-11-10 to 2023-11-17",
            "duration_days": 7,
            "purpose": "vacation",
            "total_cost": 3450.00,
            "flights": 1,
            "hotels": 2,
            "activities_booked": 5,
            "rating": 5,
            "notes": "Amazing trip! Cherry blossoms were beautiful."
        },
        {
            "trip_id": "TRIP2023_067",
            "destination": "London, UK",
            "dates": "2023-09-05 to 2023-09-12",
            "duration_days": 7,
            "purpose": "business",
            "total_cost": 2890.00,
            "flights": 1,
            "hotels": 1,
            "activities_booked": 2,
            "rating": 4,
            "notes": "Great hotel near conference center."
        },
        {
            "trip_id": "TRIP2023_045",
            "destination": "Cancun, Mexico",
            "dates": "2023-07-20 to 2023-07-27",
            "duration_days": 7,
            "purpose": "vacation",
            "total_cost": 2100.00,
            "flights": 1,
            "hotels": 1,
            "activities_booked": 4,
            "rating": 5,
            "notes": "Perfect beach vacation."
        }
    ]
    
    return {
        "trips": trips[:limit],
        "total_trips": len(trips),
        "total_spent": sum(t["total_cost"] for t in trips),
        "countries_visited": 15,
        "total_nights": 124
    }


def get_saved_payment_methods__controlled() -> List[Dict[str, Any]]:
    """Get user's saved payment methods."""
    return {
        "payment_methods": [
            {
                "id": "pm_001",
                "type": "credit_card",
                "brand": "Visa",
                "last_four": "4242",
                "expiry": "12/2026",
                "cardholder_name": "John Smith",
                "billing_address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94102",
                    "country": "US"
                },
                "is_default": True
            },
            {
                "id": "pm_002",
                "type": "credit_card",
                "brand": "Mastercard",
                "last_four": "8888",
                "expiry": "09/2025",
                "cardholder_name": "John Smith",
                "billing_address": {
                    "street": "123 Main St",
                    "city": "San Francisco",
                    "state": "CA",
                    "zip": "94102",
                    "country": "US"
                },
                "is_default": False
            }
        ]
    }


def get_travel_credits__controlled() -> Dict[str, Any]:
    """Get user's available travel credits and vouchers."""
    return {
        "credits": [
            {
                "id": "credit_001",
                "type": "airline_voucher",
                "provider": "United Airlines",
                "amount": 250.00,
                "currency": "USD",
                "expiry": "2024-12-31",
                "restrictions": "Valid for domestic flights only",
                "original_booking": "BK654321"
            },
            {
                "id": "credit_002",
                "type": "hotel_credit",
                "provider": "Marriott",
                "amount": 150.00,
                "currency": "USD",
                "expiry": "2024-06-30",
                "restrictions": "Valid at US properties only",
                "reason": "Customer service recovery"
            }
        ],
        "total_value": 400.00,
        "expiring_soon": [
            {
                "id": "credit_002",
                "amount": 150.00,
                "expires_in_days": 45
            }
        ]
    }


def get_upcoming_trips__controlled() -> List[Dict[str, Any]]:
    """Get user's upcoming confirmed trips."""
    return {
        "trips": [
            {
                "trip_id": "TRIP2024_012",
                "destination": "New York, NY",
                "departure_date": "2024-02-15",
                "return_date": "2024-02-18",
                "days_until_departure": 12,
                "status": "confirmed",
                "bookings": {
                    "flight": True,
                    "hotel": True,
                    "car": True
                },
                "total_cost": 1591.27,
                "checklist": {
                    "passport_check": True,
                    "travel_insurance": False,
                    "activities_booked": True,
                    "mobile_checkin": False
                }
            },
            {
                "trip_id": "TRIP2024_023",
                "destination": "Paris, France",
                "departure_date": "2024-04-10",
                "return_date": "2024-04-20",
                "days_until_departure": 68,
                "status": "partially_booked",
                "bookings": {
                    "flight": True,
                    "hotel": False,
                    "car": False
                },
                "total_cost": 1200.00,
                "checklist": {
                    "passport_check": True,
                    "travel_insurance": False,
                    "activities_booked": False,
                    "mobile_checkin": False
                }
            }
        ]
    }


def update_traveler_profile__controlled(traveler_id: str, **updates) -> Dict[str, Any]:
    """Update traveler profile information."""
    return {
        "success": True,
        "traveler_id": traveler_id,
        "updated_fields": list(updates.keys()),
        "message": "Traveler profile updated successfully",
        "timestamp": datetime.now().isoformat()
    }


def request_travel_approval__controlled(
    destination: str,
    departure_date: str,
    return_date: str,
    estimated_cost: float,
    business_justification: str
) -> Dict[str, Any]:
    """Submit travel request for corporate approval."""
    request_id = f"REQ-{random.randint(10000, 99999)}"
    
    return {
        "success": True,
        "request_id": request_id,
        "status": "pending",
        "destination": destination,
        "dates": f"{departure_date} to {return_date}",
        "estimated_cost": estimated_cost,
        "submitted_at": datetime.now().isoformat(),
        "approver": "Sarah Chen (Manager)",
        "expected_response": "within 2 business days",
        "policy_compliance": {
            "within_budget": True,
            "advance_notice": True,
            "preferred_vendors": True
        },
        "message": f"Travel request {request_id} submitted successfully"
    }


# ============================================================================
# PUBLIC TOOLS - General travel information and search
# ============================================================================

def search_flights__public(
    origin: str,
    destination: str,
    departure_date: str,
    return_date: str = None,
    passengers: int = 1,
    cabin_class: str = "economy"
) -> List[Dict[str, Any]]:
    """Search for available flights."""
    airlines = ["United Airlines", "Delta", "American Airlines", "Southwest", "JetBlue"]
    
    flights = []
    for i in range(5):
        base_price = random.randint(200, 800)
        dep_time = datetime.strptime(departure_date, "%Y-%m-%d") + timedelta(hours=random.randint(6, 20))
        duration_hours = random.randint(2, 8)
        
        flight = {
            "flight_id": f"FLT{random.randint(10000, 99999)}",
            "airline": random.choice(airlines),
            "flight_number": f"{random.choice(['UA', 'DL', 'AA', 'WN', 'B6'])}{random.randint(100, 9999)}",
            "departure": {
                "airport": origin,
                "time": dep_time.strftime("%Y-%m-%d %H:%M"),
                "terminal": random.choice(["1", "2", "3", "A", "B"])
            },
            "arrival": {
                "airport": destination,
                "time": (dep_time + timedelta(hours=duration_hours)).strftime("%Y-%m-%d %H:%M"),
                "terminal": random.choice(["1", "2", "3", "A", "B"])
            },
            "duration": f"{duration_hours}h {random.randint(0, 59)}m",
            "stops": random.choice([0, 0, 0, 1]),
            "price": base_price * passengers,
            "cabin_class": cabin_class,
            "seats_available": random.randint(3, 50),
            "amenities": random.sample(["wifi", "power_outlets", "entertainment", "meals"], k=random.randint(2, 4))
        }
        
        if flight["stops"] > 0:
            flight["layover"] = {
                "airport": random.choice(["ORD", "DFW", "ATL", "DEN"]),
                "duration": f"{random.randint(1, 4)}h {random.randint(0, 59)}m"
            }
        
        flights.append(flight)
    
    # Sort by price
    flights.sort(key=lambda x: x["price"])
    
    return {
        "search_params": {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "passengers": passengers,
            "cabin_class": cabin_class
        },
        "results": flights,
        "count": len(flights)
    }


def search_hotels__public(
    location: str,
    check_in: str,
    check_out: str,
    guests: int = 2,
    rooms: int = 1,
    min_stars: int = 3
) -> List[Dict[str, Any]]:
    """Search for available hotels."""
    hotel_chains = ["Marriott", "Hilton", "Hyatt", "InterContinental", "Sheraton", "Westin"]
    hotel_types = ["Hotel", "Inn & Suites", "Resort", "Grand Hotel"]
    
    hotels = []
    for i in range(8):
        stars = random.randint(min_stars, 5)
        base_price = stars * random.randint(40, 80)
        
        check_in_date = datetime.strptime(check_in, "%Y-%m-%d")
        check_out_date = datetime.strptime(check_out, "%Y-%m-%d")
        nights = (check_out_date - check_in_date).days
        
        hotel = {
            "hotel_id": f"HTL{random.randint(10000, 99999)}",
            "name": f"{random.choice(hotel_chains)} {random.choice(hotel_types)}",
            "stars": stars,
            "rating": round(random.uniform(3.5, 5.0), 1),
            "review_count": random.randint(100, 5000),
            "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Broadway', 'Park', 'Central'])} {random.choice(['St', 'Ave', 'Blvd'])}, {location}",
            "distance_from_center": f"{random.uniform(0.5, 5.0):.1f} miles",
            "price_per_night": base_price,
            "total_price": base_price * nights * rooms,
            "rooms_available": random.randint(2, 20),
            "room_type": random.choice(["Standard King", "Deluxe Queen", "Suite", "Double Queen"]),
            "amenities": random.sample([
                "Free WiFi", "Pool", "Gym", "Spa", "Restaurant",
                "Room Service", "Business Center", "Parking", "Airport Shuttle",
                "Pet Friendly", "Breakfast Included"
            ], k=random.randint(5, 9)),
            "cancellation_policy": random.choice(["Free cancellation until 24h before", "Free cancellation until 48h before", "Non-refundable"]),
            "loyalty_program": True if random.random() > 0.3 else False
        }
        
        hotels.append(hotel)
    
    # Sort by rating
    hotels.sort(key=lambda x: x["rating"], reverse=True)
    
    return {
        "search_params": {
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "rooms": rooms,
            "nights": nights
        },
        "results": hotels,
        "count": len(hotels)
    }


def search_car_rentals__public(
    pickup_location: str,
    pickup_date: str,
    dropoff_date: str,
    car_type: str = "any"
) -> List[Dict[str, Any]]:
    """Search for available car rentals."""
    companies = ["Hertz", "Enterprise", "Avis", "Budget", "National", "Alamo"]
    car_types = {
        "economy": ["Toyota Yaris", "Hyundai Accent", "Chevrolet Spark"],
        "compact": ["Honda Civic", "Toyota Corolla", "Nissan Sentra"],
        "midsize": ["Toyota Camry", "Honda Accord", "Nissan Altima"],
        "suv": ["Toyota RAV4", "Honda CR-V", "Ford Escape"],
        "luxury": ["BMW 3 Series", "Mercedes C-Class", "Audi A4"]
    }
    
    pickup_dt = datetime.strptime(pickup_date, "%Y-%m-%d")
    dropoff_dt = datetime.strptime(dropoff_date, "%Y-%m-%d")
    days = (dropoff_dt - pickup_dt).days
    
    rentals = []
    categories = [car_type] if car_type != "any" else list(car_types.keys())
    
    for category in categories:
        for company in random.sample(companies, k=3):
            daily_rate = {
                "economy": random.randint(35, 50),
                "compact": random.randint(45, 65),
                "midsize": random.randint(55, 80),
                "suv": random.randint(70, 110),
                "luxury": random.randint(120, 200)
            }[category]
            
            rental = {
                "rental_id": f"CAR{random.randint(10000, 99999)}",
                "company": company,
                "car_type": category,
                "vehicle": random.choice(car_types[category]),
                "or_similar": True,
                "passengers": random.randint(4, 7),
                "luggage": random.randint(2, 4),
                "transmission": random.choice(["Automatic", "Automatic", "Manual"]),
                "daily_rate": daily_rate,
                "total_price": daily_rate * days,
                "mileage": random.choice(["Unlimited", f"{random.randint(100, 300)} miles/day"]),
                "fuel_policy": "Full to Full",
                "insurance_included": False,
                "pickup_location": f"{company} - {pickup_location}",
                "features": random.sample([
                    "GPS Navigation", "Bluetooth", "Backup Camera",
                    "USB Charging", "Apple CarPlay", "Android Auto"
                ], k=random.randint(2, 4))
            }
            
            rentals.append(rental)
    
    # Sort by price
    rentals.sort(key=lambda x: x["total_price"])
    
    return {
        "search_params": {
            "pickup_location": pickup_location,
            "pickup_date": pickup_date,
            "dropoff_date": dropoff_date,
            "rental_days": days
        },
        "results": rentals[:10],
        "count": len(rentals[:10])
    }


def get_airport_info__public(airport_code: str) -> Dict[str, Any]:
    """Get detailed information about an airport."""
    airports = {
        "JFK": {
            "name": "John F. Kennedy International Airport",
            "city": "New York",
            "country": "United States",
            "timezone": "America/New_York"
        },
        "LAX": {
            "name": "Los Angeles International Airport",
            "city": "Los Angeles",
            "country": "United States",
            "timezone": "America/Los_Angeles"
        },
        "ORD": {
            "name": "O'Hare International Airport",
            "city": "Chicago",
            "country": "United States",
            "timezone": "America/Chicago"
        }
    }
    
    base_info = airports.get(airport_code.upper(), {
        "name": f"{airport_code} International Airport",
        "city": "Unknown",
        "country": "Unknown",
        "timezone": "UTC"
    })
    
    return {
        "code": airport_code.upper(),
        **base_info,
        "terminals": random.randint(2, 8),
        "airlines": random.randint(30, 100),
        "destinations": random.randint(100, 300),
        "facilities": [
            "Restaurants & Cafes",
            "Duty-Free Shopping",
            "Lounges",
            "Free WiFi",
            "Currency Exchange",
            "ATMs",
            "Baggage Storage",
            "Medical Services",
            "Prayer Rooms",
            "Charging Stations"
        ],
        "transportation": {
            "taxi": True,
            "rideshare": True,
            "public_transit": True,
            "rental_cars": True,
            "hotel_shuttles": True
        },
        "parking": {
            "short_term": True,
            "long_term": True,
            "economy": True,
            "daily_rate": f"\${random.randint(15, 40)}"
        },
        "contact": {
            "phone": "+1-800-123-4567",
            "website": f"https://www.{airport_code.lower()}airport.com"
        }
    }


def check_visa_requirements__public(
    destination_country: str,
    passport_country: str,
    trip_duration_days: int = 7
) -> Dict[str, Any]:
    """Check visa requirements for travel."""
    visa_types = ["visa_free", "visa_on_arrival", "evisa_required", "visa_required"]
    requirement = random.choice(visa_types)
    
    result = {
        "destination": destination_country,
        "passport": passport_country,
        "requirement_type": requirement,
        "max_stay_days": random.choice([30, 60, 90, 180])
    }
    
    if requirement == "visa_free":
        result["details"] = {
            "description": f"Citizens of {passport_country} can enter {destination_country} without a visa",
            "max_stay": f"{result['max_stay_days']} days",
            "requirements": ["Valid passport (6 months validity)", "Return ticket", "Proof of sufficient funds"],
            "processing_time": None,
            "cost": 0
        }
    elif requirement == "visa_on_arrival":
        result["details"] = {
            "description": f"Visa on arrival available for citizens of {passport_country}",
            "max_stay": f"{result['max_stay_days']} days",
            "requirements": ["Valid passport (6 months validity)", "Passport photo", "Visa fee in cash"],
            "processing_time": "At airport (30-60 minutes)",
            "cost": random.randint(20, 100)
        }
    elif requirement == "evisa_required":
        result["details"] = {
            "description": f"Electronic visa (eVisa) required for citizens of {passport_country}",
            "max_stay": f"{result['max_stay_days']} days",
            "requirements": ["Valid passport (6 months validity)", "Digital passport photo", "Travel itinerary", "Hotel booking"],
            "processing_time": "3-5 business days",
            "cost": random.randint(30, 150),
            "application_url": f"https://evisa.{destination_country.lower()}.gov"
        }
    else:
        result["details"] = {
            "description": f"Visa required for citizens of {passport_country}",
            "max_stay": f"{result['max_stay_days']} days",
            "requirements": ["Valid passport (6 months validity)", "Completed application form", "Passport photos", "Travel itinerary", "Hotel bookings", "Financial proof", "Employment letter"],
            "processing_time": "10-15 business days",
            "cost": random.randint(100, 300),
            "embassy_appointment": True
        }
    
    return result


def get_destination_weather__public(location: str, date: str = None) -> Dict[str, Any]:
    """Get weather forecast for travel destination."""
    target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    
    # Generate 7-day forecast
    forecast = []
    for i in range(7):
        day = target_date + timedelta(days=i)
        temp_high = random.randint(65, 85)
        temp_low = temp_high - random.randint(10, 20)
        
        forecast.append({
            "date": day.strftime("%Y-%m-%d"),
            "day_name": day.strftime("%A"),
            "high": temp_high,
            "low": temp_low,
            "condition": random.choice(["Sunny", "Partly Cloudy", "Cloudy", "Rain", "Thunderstorms"]),
            "precipitation_chance": random.randint(0, 100),
            "humidity": random.randint(40, 80),
            "wind_mph": random.randint(5, 20)
        })
    
    return {
        "location": location,
        "current": forecast[0],
        "forecast": forecast[1:],
        "best_time_to_visit": "Spring (March-May) or Fall (September-November)",
        "packing_suggestions": [
            "Light jacket for evenings",
            "Comfortable walking shoes",
            "Sunscreen and sunglasses",
            "Umbrella (rain possible)"
        ]
    }


def get_currency_exchange__public(from_currency: str, to_currency: str, amount: float = 1.0) -> Dict[str, Any]:
    """Get currency exchange rates and conversion."""
    # Mock exchange rates
    rates = {
        ("USD", "EUR"): 0.92,
        ("USD", "GBP"): 0.79,
        ("USD", "JPY"): 149.50,
        ("USD", "CAD"): 1.35,
        ("EUR", "USD"): 1.09,
        ("GBP", "USD"): 1.27
    }
    
    rate = rates.get((from_currency.upper(), to_currency.upper()), 1.0)
    converted_amount = amount * rate
    
    return {
        "from": {
            "currency": from_currency.upper(),
            "amount": amount
        },
        "to": {
            "currency": to_currency.upper(),
            "amount": round(converted_amount, 2)
        },
        "rate": rate,
        "last_updated": datetime.now().isoformat(),
        "tips": {
            "best_exchange_method": "Use ATMs at destination for best rates",
            "avoid": "Airport currency exchanges (high fees)",
            "credit_cards": "Notify your bank before traveling",
            "cash_recommendation": f"Carry \${random.randint(100, 300)} in local currency for emergencies"
        }
    }


def find_attractions__public(location: str, category: str = "all", top_n: int = 10) -> List[Dict[str, Any]]:
    """Find tourist attractions and activities."""
    categories_list = ["museum", "landmark", "park", "entertainment", "shopping", "food_tour", "adventure"]
    
    attractions = []
    selected_categories = [category] if category != "all" else random.sample(categories_list, k=5)
    
    for cat in selected_categories:
        for i in range(2):
            attraction = {
                "id": f"attr_{random.randint(10000, 99999)}",
                "name": f"{random.choice(['Famous', 'Historic', 'Popular', 'Beautiful', 'Amazing'])} {cat.replace('_', ' ').title()}",
                "category": cat,
                "rating": round(random.uniform(4.0, 5.0), 1),
                "review_count": random.randint(500, 10000),
                "price_level": random.choice(["\$", "\$\$", "\$\$\$", "\$\$\$\$"]),
                "duration": f"{random.randint(1, 4)} hours",
                "location": location,
                "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Broadway', 'Market'])} St",
                "description": f"One of the most popular {cat}s in {location}. Don't miss this must-see attraction!",
                "opening_hours": "9:00 AM - 6:00 PM",
                "admission": {
                    "adult": random.randint(15, 50),
                    "child": random.randint(8, 25),
                    "senior": random.randint(10, 40)
                },
                "best_time_to_visit": random.choice(["Morning", "Afternoon", "Evening", "Weekdays"]),
                "accessibility": random.choice([True, True, False])
            }
            attractions.append(attraction)
    
    # Sort by rating
    attractions.sort(key=lambda x: x["rating"], reverse=True)
    
    return {
        "location": location,
        "category": category,
        "attractions": attractions[:top_n],
        "count": len(attractions[:top_n])
    }


def search_restaurants__public(
    location: str,
    cuisine: str = "any",
    price_range: str = "any",
    meal_type: str = "any"
) -> List[Dict[str, Any]]:
    """Search for restaurants at destination."""
    cuisines = ["Italian", "Japanese", "Mexican", "French", "American", "Chinese", "Thai", "Indian", "Mediterranean"]
    
    restaurants = []
    for i in range(8):
        selected_cuisine = cuisine if cuisine != "any" else random.choice(cuisines)
        stars = round(random.uniform(3.5, 5.0), 1)
        
        price = price_range if price_range != "any" else random.choice(["\$", "\$\$", "\$\$\$", "\$\$\$\$"])
        
        restaurant = {
            "id": f"rest_{random.randint(10000, 99999)}",
            "name": f"{random.choice(['The', 'Le', 'La', 'Il', 'Chez'])} {random.choice(['Garden', 'Kitchen', 'Bistro', 'House', 'Place'])}",
            "cuisine": selected_cuisine,
            "rating": stars,
            "review_count": random.randint(100, 5000),
            "price_range": price,
            "location": location,
            "address": f"{random.randint(100, 9999)} {random.choice(['Main', 'Broadway', 'Park'])} St",
            "phone": f"+1-555-{random.randint(1000, 9999)}",
            "hours": {
                "lunch": "11:30 AM - 2:30 PM",
                "dinner": "5:30 PM - 10:00 PM"
            },
            "specialties": random.sample([
                "Fresh Seafood", "Pasta", "Steaks", "Vegetarian Options",
                "Sushi", "Wine Selection", "Craft Cocktails", "Desserts"
            ], k=3),
            "features": random.sample([
                "Outdoor Seating", "Reservations Recommended", "Romantic",
                "Family Friendly", "Groups Welcome", "Private Dining",
                "Live Music", "View", "Michelin Star"
            ], k=random.randint(2, 5)),
            "reservation_required": stars >= 4.5,
            "dress_code": "Casual" if price in ["\$", "\$\$"] else "Smart Casual"
        }
        
        restaurants.append(restaurant)
    
    # Sort by rating
    restaurants.sort(key=lambda x: x["rating"], reverse=True)
    
    return {
        "location": location,
        "filters": {
            "cuisine": cuisine,
            "price_range": price_range,
            "meal_type": meal_type
        },
        "restaurants": restaurants,
        "count": len(restaurants)
    }


def get_travel_alerts__public(destination: str) -> Dict[str, Any]:
    """Get travel advisories and safety information."""
    alert_levels = ["Level 1: Exercise Normal Precautions", "Level 2: Exercise Increased Caution", "Level 3: Reconsider Travel", "Level 4: Do Not Travel"]
    
    return {
        "destination": destination,
        "advisory_level": random.choice(alert_levels[:2]),  # Mostly safe levels
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "summary": f"Exercise normal precautions when traveling to {destination}.",
        "health_alerts": [
            {
                "type": "vaccination",
                "title": "Routine Vaccinations",
                "description": "Make sure you are up-to-date on routine vaccines",
                "severity": "info"
            },
            {
                "type": "health",
                "title": "Travel Health Notice",
                "description": "Stay informed about local health conditions",
                "severity": "low"
            }
        ],
        "safety_tips": [
            "Keep copies of important documents",
            "Register with your embassy",
            "Be aware of your surroundings",
            "Avoid displaying wealth",
            "Use reputable transportation",
            "Stay in well-lit areas at night"
        ],
        "emergency_contacts": {
            "police": "911" if "United States" in destination else "112",
            "ambulance": "911" if "United States" in destination else "112",
            "us_embassy": f"+{random.randint(10, 99)}-{random.randint(100, 999)}-{random.randint(1000, 9999)}"
        },
        "local_laws": [
            "Drinking age: 21 years",
            "Smoking restrictions apply in public areas",
            "Drugs: Strictly prohibited",
            "Photography: Restricted in some government buildings"
        ]
    }


def calculate_trip_cost__public(
    destination: str,
    duration_days: int,
    travelers: int = 1,
    travel_style: str = "moderate"
) -> Dict[str, Any]:
    """Estimate total trip cost."""
    style_multipliers = {
        "budget": 0.6,
        "moderate": 1.0,
        "luxury": 2.0
    }
    
    multiplier = style_multipliers.get(travel_style, 1.0)
    
    # Base daily costs
    accommodation = random.randint(80, 150) * multiplier * duration_days * travelers
    food = random.randint(40, 70) * multiplier * duration_days * travelers
    activities = random.randint(30, 60) * multiplier * duration_days * travelers
    local_transport = random.randint(15, 30) * multiplier * duration_days * travelers
    flights = random.randint(400, 800) * multiplier * travelers
    
    total = accommodation + food + activities + local_transport + flights
    
    return {
        "destination": destination,
        "duration_days": duration_days,
        "travelers": travelers,
        "travel_style": travel_style,
        "breakdown": {
            "flights": round(flights, 2),
            "accommodation": round(accommodation, 2),
            "food_and_dining": round(food, 2),
            "activities": round(activities, 2),
            "local_transportation": round(local_transport, 2)
        },
        "daily_average": round(total / duration_days, 2),
        "per_person": round(total / travelers, 2),
        "total_estimate": round(total, 2),
        "contingency": round(total * 0.1, 2),  # 10% buffer
        "grand_total": round(total * 1.1, 2),
        "tips": [
            "Book flights 6-8 weeks in advance for best prices",
            "Consider shoulder season for lower costs",
            "Use public transportation to save money",
            "Book accommodation with kitchen to save on meals",
            "Look for city passes for attractions"
        ]
    }


def get_local_transportation__public(destination: str) -> Dict[str, Any]:
    """Get information about local transportation options."""
    return {
        "destination": destination,
        "public_transit": {
            "available": True,
            "types": ["Metro", "Bus", "Light Rail", "Tram"],
            "hours": "5:00 AM - 1:00 AM",
            "payment": {
                "methods": ["Cash", "Card", "Mobile App"],
                "day_pass": random.randint(8, 15),
                "week_pass": random.randint(25, 40),
                "single_ride": random.uniform(2.5, 4.0)
            },
            "app": f"{destination}Transit",
            "tourist_pass": {
                "available": True,
                "name": f"{destination} City Pass",
                "price": random.randint(40, 80),
                "includes": ["Unlimited transit", "Some attractions", "Discounts at restaurants"]
            }
        },
        "taxi": {
            "available": True,
            "base_fare": random.uniform(3.0, 5.0),
            "per_mile": random.uniform(2.0, 4.0),
            "typical_airport_fare": random.randint(35, 70),
            "apps": ["Uber", "Lyft", "Local Taxi App"]
        },
        "bike_share": {
            "available": True,
            "providers": [f"{destination}Bikes", "City Cycles"],
            "pricing": {
                "per_30min": 3.50,
                "day_pass": 15.00
            },
            "stations": random.randint(100, 500)
        },
        "car_rental": {
            "recommended": random.choice([True, False]),
            "daily_rate": random.randint(45, 90),
            "parking_costs": {
                "street": f"\${random.randint(2, 5)}/hour",
                "garage": f"\${random.randint(20, 40)}/day"
            },
            "notes": "Consider parking costs and traffic before renting"
        },
        "tips": [
            "Download the local transit app before arrival",
            "Get a transit card for convenience",
            "Avoid rush hours (7-9 AM, 5-7 PM)",
            "Walking is often the best way to explore downtown"
        ]
    }


def find_travel_insurance__public(
    trip_cost: float,
    travelers: int,
    duration_days: int,
    destination: str
) -> List[Dict[str, Any]]:
    """Find travel insurance options."""
    providers = ["Allianz", "Travel Guard", "World Nomads", "InsureMyTrip", "Travelex"]
    
    plans = []
    for provider in providers[:4]:
        base_cost = trip_cost * 0.05  # ~5% of trip cost
        cost = base_cost * travelers * (1 + random.uniform(-0.3, 0.3))
        
        plan = {
            "provider": provider,
            "plan_name": random.choice(["Essential", "Preferred", "Premium", "Elite"]),
            "cost": round(cost, 2),
            "coverage": {
                "trip_cancellation": round(trip_cost, 2),
                "medical_expenses": random.choice([50000, 100000, 250000]),
                "emergency_evacuation": random.choice([250000, 500000]),
                "baggage_loss": random.randint(1000, 3000),
                "travel_delay": random.randint(500, 1500)
            },
            "benefits": random.sample([
                "24/7 Emergency Assistance",
                "Cancel for Any Reason (CFAR)",
                "Pre-existing Conditions Coverage",
                "Adventure Sports Coverage",
                "Rental Car Coverage",
                "Identity Theft Protection",
                "Missed Connection Coverage"
            ], k=random.randint(4, 7)),
            "deductible": random.choice([0, 50, 100, 250]),
            "rating": round(random.uniform(4.0, 5.0), 1),
            "best_for": random.choice([
                "Best Value",
                "Most Comprehensive",
                "Best for Adventure Travel",
                "Best Medical Coverage"
            ])
        }
        
        plans.append(plan)
    
    # Sort by cost
    plans.sort(key=lambda x: x["cost"])
    
    return {
        "trip_details": {
            "cost": trip_cost,
            "travelers": travelers,
            "duration_days": duration_days,
            "destination": destination
        },
        "plans": plans,
        "count": len(plans),
        "tips": [
            "Buy insurance soon after booking your trip",
            "Consider CFAR if you want flexibility",
            "Check if your credit card provides travel insurance",
            "Read the policy exclusions carefully",
            "Keep emergency contact numbers handy"
        ]
    }


def get_packing_checklist__public(
    destination: str,
    duration_days: int,
    season: str,
    trip_type: str = "leisure"
) -> Dict[str, Any]:
    """Generate a packing checklist based on trip details."""
    
    essentials = [
        "Passport/ID",
        "Travel insurance documents",
        "Flight tickets/confirmations",
        "Hotel reservations",
        "Credit cards & cash",
        "Phone & charger",
        "Power adapter (if international)",
        "Medications",
        "Copies of important documents"
    ]
    
    clothing_base = [
        f"{duration_days + 1} underwear",
        f"{duration_days + 1} socks",
        f"{duration_days - 1} shirts/tops",
        f"{duration_days // 2} pants/shorts",
        "1-2 pairs of shoes",
        "Sleepwear",
        "Jacket/sweater"
    ]
    
    if season in ["winter", "fall"]:
        clothing_base.extend(["Warm coat", "Gloves", "Scarf", "Hat"])
    else:
        clothing_base.extend(["Sunglasses", "Hat/cap", "Swimsuit"])
    
    toiletries = [
        "Toothbrush & toothpaste",
        "Shampoo & conditioner",
        "Soap/body wash",
        "Deodorant",
        "Sunscreen",
        "Lip balm",
        "Razor",
        "Hairbrush/comb",
        "Feminine hygiene products (if needed)"
    ]
    
    electronics = [
        "Phone charger",
        "Portable battery pack",
        "Camera (optional)",
        "Headphones",
        "Laptop/tablet (if needed)",
        "E-reader (optional)"
    ]
    
    misc_items = [
        "Reusable water bottle",
        "Day backpack",
        "Umbrella",
        "Hand sanitizer",
        "Tissues",
        "Ziplock bags",
        "Travel pillow",
        "Eye mask & earplugs"
    ]
    
    if trip_type == "business":
        clothing_base.extend(["Business attire", "Dress shoes", "Belt", "Tie (if applicable)"])
        electronics.extend(["Laptop", "Business cards", "Notebook & pen"])
    elif trip_type == "adventure":
        misc_items.extend(["Hiking boots", "Backpack", "First aid kit", "Multi-tool", "Flashlight"])
    elif trip_type == "beach":
        misc_items.extend(["Beach towel", "Snorkel gear", "Flip flops", "Beach bag", "Waterproof phone case"])
    
    return {
        "destination": destination,
        "duration_days": duration_days,
        "season": season,
        "trip_type": trip_type,
        "checklist": {
            "essentials": essentials,
            "clothing": clothing_base,
            "toiletries": toiletries,
            "electronics": electronics,
            "miscellaneous": misc_items
        },
        "baggage_tips": [
            f"For {duration_days} days, a {['carry-on', 'carry-on', 'checked bag'][min(duration_days // 4, 2)]} should suffice",
            "Roll clothes to save space",
            "Wear bulkiest items on the plane",
            "Check airline baggage restrictions",
            "Keep valuables in carry-on",
            "Pack a change of clothes in carry-on"
        ],
        "total_items": sum([
            len(essentials),
            len(clothing_base),
            len(toiletries),
            len(electronics),
            len(misc_items)
        ])
    }