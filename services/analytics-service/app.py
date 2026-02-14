"""
Analytics Service - Risk zone analysis, demographic patterns, predictive insights
Port: 5005
"""
import os
import math
from datetime import datetime
from functools import wraps
from collections import Counter
from flask import Flask, request, jsonify

# Import shared components
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from shared.config import Config
from shared.models import db, MissingChild, RiskZone, Analytics


app = Flask(__name__)
app.config.from_object(Config)

# Initialize database
db.init_app(app)


# ==================== AUTHENTICATION MIDDLEWARE ====================

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-Service-API-Key')
        expected_key = os.environ.get('SERVICE_API_KEY', 'dev-service-key-change-in-production')

        if not api_key or api_key != expected_key:
            return jsonify({'error': 'Unauthorized', 'success': False}), 401

        return f(*args, **kwargs)
    return decorated_function


# ==================== HELPER FUNCTIONS ====================

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two coordinates using Haversine formula (in km)"""
    R = 6371  # Earth's radius in kilometers

    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

    return R * c


def calculate_risk_score(cases):
    """Calculate risk score for a zone based on multiple factors"""
    if not cases:
        return 0

    # Incident count score (0-50 points)
    incident_score = min(len(cases) * 10, 50)

    # Recency score (0-20 points based on how recent the cases are)
    now = datetime.utcnow()
    recency_scores = []

    for case in cases:
        days_ago = (now - case.created_at).days
        if days_ago <= 30:
            recency_scores.append(20)
        elif days_ago <= 90:
            recency_scores.append(15)
        elif days_ago <= 365:
            recency_scores.append(10)
        else:
            recency_scores.append(5)

    recency_score = sum(recency_scores) / len(recency_scores) if recency_scores else 0

    # Age vulnerability score (0-15 points - younger children = higher score)
    age_scores = []
    for case in cases:
        if case.age <= 5:
            age_scores.append(15)
        elif case.age <= 10:
            age_scores.append(12)
        elif case.age <= 15:
            age_scores.append(8)
        else:
            age_scores.append(5)

    age_score = sum(age_scores) / len(age_scores) if age_scores else 0

    # Total score (max 100)
    total_score = incident_score + recency_score + age_score
    return min(total_score, 100)


def get_age_group(age):
    """Helper function to get age group"""
    if age <= 5:
        return '0-5 years'
    elif age <= 10:
        return '6-10 years'
    elif age <= 15:
        return '11-15 years'
    else:
        return '16+ years'


# ==================== HEALTH CHECK ====================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db.session.execute(db.select(MissingChild).limit(1))
        return jsonify({
            'status': 'healthy',
            'service': 'analytics-service',
            'port': 5005,
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'service': 'analytics-service',
            'error': str(e)
        }), 503


# ==================== RISK ZONES ====================

@app.route('/api/analytics/risk-zones', methods=['GET'])
@require_api_key
def get_risk_zones():
    """Get all risk zones from database"""
    try:
        zones = db.session.execute(
            db.select(RiskZone).order_by(RiskZone.risk_score.desc())
        ).scalars().all()

        zones_list = [{
            'id': zone.id,
            'zone_name': zone.zone_name,
            'latitude': zone.latitude,
            'longitude': zone.longitude,
            'risk_score': zone.risk_score,
            'incident_count': zone.incident_count,
            'radius_km': zone.radius_km,
            'last_updated': zone.last_updated.isoformat()
        } for zone in zones]

        return jsonify({
            'success': True,
            'risk_zones': zones_list,
            'count': len(zones_list)
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to fetch risk zones: {str(e)}',
            'success': False
        }), 500


@app.route('/api/analytics/risk-zones/update', methods=['POST'])
@require_api_key
def update_risk_zones():
    """
    Recalculate risk zones based on current case data

    Algorithm:
    1. Get all cases with coordinates
    2. Cluster cases within 2km radius
    3. Calculate risk score for each cluster
    4. Save to database
    """
    try:
        # Get all cases with coordinates
        cases = db.session.execute(
            db.select(MissingChild)
            .where(MissingChild.lat.isnot(None))
            .where(MissingChild.lng.isnot(None))
        ).scalars().all()

        if len(cases) < 2:
            return jsonify({
                'success': True,
                'message': 'Not enough cases with coordinates to calculate risk zones',
                'zones_created': 0
            }), 200

        zones = []
        processed = set()

        # Clustering algorithm - group cases within 2km
        for i, case in enumerate(cases):
            if i in processed:
                continue

            zone_cases = [case]
            processed.add(i)

            # Find nearby cases
            for j, other_case in enumerate(cases[i+1:], i+1):
                if j in processed:
                    continue

                distance = calculate_distance(
                    case.lat, case.lng,
                    other_case.lat, other_case.lng
                )

                if distance <= 2.0:  # 2km radius
                    zone_cases.append(other_case)
                    processed.add(j)

            # Only create zone if 2+ cases in cluster
            if len(zone_cases) >= 2:
                avg_lat = sum(c.lat for c in zone_cases) / len(zone_cases)
                avg_lng = sum(c.lng for c in zone_cases) / len(zone_cases)
                risk_score = calculate_risk_score(zone_cases)
                zone_name = f"Zone_{len(zones)+1}"

                zones.append({
                    'name': zone_name,
                    'lat': avg_lat,
                    'lng': avg_lng,
                    'risk_score': risk_score,
                    'incident_count': len(zone_cases)
                })

        # Clear existing zones and save new ones
        db.session.execute(db.delete(RiskZone))

        for zone in zones:
            risk_zone = RiskZone(
                zone_name=zone['name'],
                latitude=zone['lat'],
                longitude=zone['lng'],
                risk_score=zone['risk_score'],
                incident_count=zone['incident_count'],
                radius_km=2.0
            )
            db.session.add(risk_zone)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Risk zones updated successfully',
            'zones_created': len(zones)
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'error': f'Failed to update risk zones: {str(e)}',
            'success': False
        }), 500


# ==================== DEMOGRAPHICS ====================

@app.route('/api/analytics/demographics', methods=['GET'])
@require_api_key
def get_demographics():
    """
    Analyze demographic patterns in missing child cases

    Returns:
    - Age group distribution
    - Gender distribution
    - Time patterns (when incidents occur)
    - Location type patterns
    - Recovery rates
    """
    try:
        cases = db.session.execute(db.select(MissingChild)).scalars().all()

        if not cases:
            return jsonify({
                'success': True,
                'patterns': {},
                'message': 'No cases available for analysis'
            }), 200

        patterns = {
            'age_groups': {},
            'gender_distribution': {},
            'time_patterns': {},
            'location_types': {},
            'recovery_rates': {}
        }

        # Count age groups
        age_counter = Counter()
        gender_counter = Counter()
        time_counter = Counter()
        location_counter = Counter()

        for case in cases:
            # Age groups
            age_counter[get_age_group(case.age)] += 1

            # Gender distribution
            gender_counter[case.gender] += 1

            # Time patterns
            hour = case.created_at.hour
            if 6 <= hour < 12:
                time_counter['Morning (6-12)'] += 1
            elif 12 <= hour < 18:
                time_counter['Afternoon (12-18)'] += 1
            elif 18 <= hour < 24:
                time_counter['Evening (18-24)'] += 1
            else:
                time_counter['Night (0-6)'] += 1

            # Location types
            location = case.location.lower()
            if any(word in location for word in ['park', 'playground']):
                location_counter['Parks/Playgrounds'] += 1
            elif any(word in location for word in ['school', 'university', 'college']):
                location_counter['Educational'] += 1
            elif any(word in location for word in ['mall', 'store', 'shop', 'market']):
                location_counter['Commercial'] += 1
            elif any(word in location for word in ['home', 'house', 'residence']):
                location_counter['Residential'] += 1
            else:
                location_counter['Other'] += 1

        # Convert counters to dicts
        patterns['age_groups'] = dict(age_counter)
        patterns['gender_distribution'] = dict(gender_counter)
        patterns['time_patterns'] = dict(time_counter)
        patterns['location_types'] = dict(location_counter)

        # Calculate recovery rates
        found_cases = [c for c in cases if c.status == 'found']
        total_cases = len(cases)

        if total_cases > 0:
            patterns['recovery_rates']['overall'] = round((len(found_cases) / total_cases) * 100, 2)

            # Recovery rates by age group
            age_recovery = {}
            for age_group in patterns['age_groups']:
                age_cases = [c for c in cases if get_age_group(c.age) == age_group]
                age_found = [c for c in age_cases if c.status == 'found']
                if age_cases:
                    age_recovery[age_group] = round((len(age_found) / len(age_cases)) * 100, 2)

            patterns['recovery_rates']['by_age'] = age_recovery

        return jsonify({
            'success': True,
            'patterns': patterns
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to analyze demographics: {str(e)}',
            'success': False
        }), 500


# ==================== PREDICTIVE INSIGHTS ====================

@app.route('/api/analytics/insights', methods=['GET'])
@require_api_key
def get_insights():
    """
    Generate human-readable predictive insights

    Analyzes:
    - High-risk zones
    - Vulnerable demographics
    - Peak incident times
    - Common locations
    - Recovery rates
    """
    try:
        # Get risk zones
        zones = db.session.execute(
            db.select(RiskZone).order_by(RiskZone.risk_score.desc())
        ).scalars().all()

        # Get demographic patterns
        cases = db.session.execute(db.select(MissingChild)).scalars().all()

        insights = []

        # Risk zone insights
        if zones:
            high_risk_zones = [z for z in zones if z.risk_score > 70]
            medium_risk_zones = [z for z in zones if 40 <= z.risk_score <= 70]

            if high_risk_zones:
                insights.append({
                    'type': 'high_risk',
                    'icon': '🔴',
                    'message': f"HIGH RISK: {len(high_risk_zones)} zones identified with elevated risk (score >70)"
                })
            if medium_risk_zones:
                insights.append({
                    'type': 'medium_risk',
                    'icon': '🟡',
                    'message': f"MEDIUM RISK: {len(medium_risk_zones)} zones require monitoring (score 40-70)"
                })

        # Demographic insights
        if cases:
            # Age group analysis
            age_counter = Counter()
            gender_counter = Counter()
            time_counter = Counter()
            location_counter = Counter()

            for case in cases:
                age_counter[get_age_group(case.age)] += 1
                gender_counter[case.gender] += 1

                hour = case.created_at.hour
                if 6 <= hour < 12:
                    time_counter['Morning (6-12)'] += 1
                elif 12 <= hour < 18:
                    time_counter['Afternoon (12-18)'] += 1
                elif 18 <= hour < 24:
                    time_counter['Evening (18-24)'] += 1
                else:
                    time_counter['Night (0-6)'] += 1

                location = case.location.lower()
                if any(word in location for word in ['park', 'playground']):
                    location_counter['Parks/Playgrounds'] += 1
                elif any(word in location for word in ['school', 'university']):
                    location_counter['Educational'] += 1
                elif any(word in location for word in ['mall', 'store', 'shop']):
                    location_counter['Commercial'] += 1
                elif any(word in location for word in ['home', 'house', 'residence']):
                    location_counter['Residential'] += 1
                else:
                    location_counter['Other'] += 1

            # Most vulnerable age group
            if age_counter:
                most_vulnerable = max(age_counter.items(), key=lambda x: x[1])
                insights.append({
                    'type': 'demographics',
                    'icon': '👶',
                    'message': f"DEMOGRAPHICS: {most_vulnerable[0]} age group has highest incident rate ({most_vulnerable[1]} cases)"
                })

            # Peak time
            if time_counter:
                peak_time = max(time_counter.items(), key=lambda x: x[1])
                insights.append({
                    'type': 'timing',
                    'icon': '⏰',
                    'message': f"TIMING: Most incidents occur during {peak_time[0]} ({peak_time[1]} cases)"
                })

            # Common locations
            if location_counter:
                common_location = max(location_counter.items(), key=lambda x: x[1])
                insights.append({
                    'type': 'locations',
                    'icon': '📍',
                    'message': f"LOCATIONS: {common_location[0]} areas account for most incidents ({common_location[1]} cases)"
                })

            # Recovery rate
            found_cases = [c for c in cases if c.status == 'found']
            total_cases = len(cases)

            if total_cases > 0:
                recovery_rate = (len(found_cases) / total_cases) * 100
                if recovery_rate > 80:
                    insights.append({
                        'type': 'positive',
                        'icon': '✅',
                        'message': f"POSITIVE: High recovery rate of {recovery_rate:.1f}%"
                    })
                elif recovery_rate < 50:
                    insights.append({
                        'type': 'concern',
                        'icon': '⚠️',
                        'message': f"CONCERN: Low recovery rate of {recovery_rate:.1f}% - review response protocols"
                    })

        return jsonify({
            'success': True,
            'insights': insights,
            'count': len(insights)
        }), 200

    except Exception as e:
        return jsonify({
            'error': f'Failed to generate insights: {str(e)}',
            'success': False
        }), 500


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint not found', 'success': False}), 404


@app.errorhandler(500)
def internal_error(e):
    db.session.rollback()
    return jsonify({'error': 'Internal server error', 'success': False}), 500


# ==================== RUN SERVER ====================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

    port = int(os.environ.get('PORT', 5005))
    app.run(host='0.0.0.0', port=port, debug=False)
