"""Seed data for local development and the demo.

Blood banks: real Delhi NCR blood centres with APPROXIMATE coordinates and no phone numbers
(phone and stock come from eRaktKosh at runtime). Donors: SYNTHETIC people with fake phone
numbers in the 9100000xxxxx range, which no real Indian mobile can have; the WhatsApp
service refuses to send to that range outside mock mode."""
import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from .db import Base, engine, utcnow
from .models import BloodBank, Donor

SYNTHETIC_PREFIX = "9100000"

BLOOD_BANKS = [
    ("AIIMS Main Blood Bank", "Ansari Nagar, New Delhi", 28.5672, 77.2100, "South Delhi", "Delhi", "Government"),
    ("Safdarjung Hospital Blood Bank", "Ansari Nagar West, New Delhi", 28.5683, 77.2058, "South Delhi", "Delhi", "Government"),
    ("Dr. Ram Manohar Lohia Hospital Blood Bank", "Baba Kharak Singh Marg, New Delhi", 28.6262, 77.2004, "New Delhi", "Delhi", "Government"),
    ("Lok Nayak Hospital Blood Bank", "Jawaharlal Nehru Marg, Delhi Gate", 28.6394, 77.2382, "Central Delhi", "Delhi", "Government"),
    ("Guru Teg Bahadur Hospital Blood Bank", "Dilshad Garden, Delhi", 28.6856, 77.3104, "Shahdara", "Delhi", "Government"),
    ("Indian Red Cross Society Blood Bank", "Red Cross Road, New Delhi", 28.6205, 77.2140, "New Delhi", "Delhi", "Charitable"),
    ("Sir Ganga Ram Hospital Blood Bank", "Rajinder Nagar, New Delhi", 28.6387, 77.1895, "Central Delhi", "Delhi", "Private"),
    ("Max Super Speciality Hospital Blood Bank, Saket", "Press Enclave Road, Saket", 28.5276, 77.2117, "South Delhi", "Delhi", "Private"),
    ("Indraprastha Apollo Hospital Blood Bank", "Sarita Vihar, Mathura Road", 28.5414, 77.2835, "South East Delhi", "Delhi", "Private"),
    ("Deen Dayal Upadhyay Hospital Blood Bank", "Hari Nagar, Delhi", 28.6290, 77.1150, "West Delhi", "Delhi", "Government"),
    ("Rotary Blood Bank", "Tughlakabad Institutional Area, Delhi", 28.5130, 77.2560, "South Delhi", "Delhi", "Charitable"),
    ("Fortis Memorial Research Institute Blood Bank", "Sector 44, Gurugram", 28.4570, 77.0725, "Gurugram", "Haryana", "Private"),
    ("Medanta The Medicity Blood Bank", "Sector 38, Gurugram", 28.4394, 77.0406, "Gurugram", "Haryana", "Private"),
    ("Civil Hospital Blood Bank, Gurugram", "Sadar Bazar, Gurugram", 28.4660, 77.0300, "Gurugram", "Haryana", "Government"),
    ("Fortis Hospital Blood Bank, Noida", "Sector 62, Noida", 28.6187, 77.3728, "Gautam Buddha Nagar", "Uttar Pradesh", "Private"),
    ("District Hospital Blood Bank, Noida", "Sector 30, Noida", 28.5780, 77.3420, "Gautam Buddha Nagar", "Uttar Pradesh", "Government"),
    ("Badshah Khan Civil Hospital Blood Bank", "NIT, Faridabad", 28.4060, 77.3060, "Faridabad", "Haryana", "Government"),
]

GROUP_WEIGHTS = {"O+": 35, "B+": 31, "A+": 21, "AB+": 7, "O-": 2, "B-": 2, "A-": 1.5, "AB-": 0.5}
FIRST = ["Aman", "Riya", "Kabir", "Neha", "Arjun", "Pooja", "Rohan", "Simran", "Vikram", "Ananya", "Karan", "Meera",
         "Rahul", "Sneha", "Aditya", "Priya", "Saurabh", "Kavya", "Nikhil", "Isha", "Manish", "Tanvi", "Harsh", "Divya",
         "Yash", "Aarti", "Deepak", "Nisha", "Gaurav", "Shruti", "Varun", "Pallavi", "Ankit", "Jyoti", "Siddharth", "Ritu"]
LAST = ["Sharma", "Verma", "Gupta", "Singh", "Yadav", "Malhotra", "Khanna", "Mehra", "Bansal", "Chauhan", "Kapoor",
        "Jain", "Arora", "Tiwari", "Mishra", "Rawat", "Saxena", "Bhatia", "Negi", "Ahuja"]
FEMALE = {"Riya", "Neha", "Pooja", "Simran", "Ananya", "Meera", "Sneha", "Priya", "Kavya", "Isha", "Tanvi", "Divya",
          "Aarti", "Nisha", "Shruti", "Pallavi", "Jyoti", "Ritu"}
# (lat, lng, share of donors, spread in degrees)
CLUSTERS = [(28.535, 77.215, 0.35, 0.035), (28.630, 77.210, 0.2, 0.05), (28.460, 77.050, 0.2, 0.04),
            (28.580, 77.350, 0.15, 0.04), (28.680, 77.120, 0.10, 0.05)]


def seed_blood_banks(db: Session) -> int:
    """Real eRaktKosh directory snapshot (W2) when shipped; the small hand-made list otherwise."""
    from .services import directory

    rows = directory.load_snapshot()
    if rows:
        return directory.upsert(db, rows, source="eraktkosh")["added"]
    for name, addr, lat, lng, district, state, cat in BLOOD_BANKS:
        db.add(BloodBank(name=name, address=addr, lat=lat, lng=lng, district=district, state=state,
                         category=cat, source="seed (approximate coordinates)"))
    return len(BLOOD_BANKS)


def seed_extras(db: Session) -> dict:
    """Demo data for the new features, all labelled: recurring-rota opt-ins on synthetic donors,
    one SYNTHETIC thalassemia patient with a 6-month rota, sample camps, the family-guide KB."""
    from datetime import date

    from .models import RecurringNeed
    from .services import camps, guide, recurring

    rng = random.Random(7)
    for d in db.query(Donor).filter(Donor.synthetic.is_(True)).all():
        d.recurring_opt_in = rng.random() < 0.35
    db.flush()
    need = RecurringNeed(patient_label="Baby A. (synthetic)", patient_group="B+", component="prbc", units=2, interval_days=21,
                         next_due=date.today() + timedelta(days=2), hospital_name="Sir Ganga Ram Hospital", hospital_lat=28.6387,
                         hospital_lng=77.1895, requester_name="Thalassemia family (synthetic)", requester_phone="910000000001",
                         max_km=20, synthetic=True)
    db.add(need)
    db.flush()
    slots = recurring.rebuild(db, need)
    return {"camps": camps.seed_sample(db), "guide_chunks": guide.load(db), "rota_slots": len(slots)}


def seed_donors(db: Session, n: int = 200, seed: int = 42) -> int:
    rng = random.Random(seed)
    today = date.today()
    groups, weights = zip(*GROUP_WEIGHTS.items())
    for i in range(n):
        first = rng.choice(FIRST)
        r, acc = rng.random(), 0.0
        for lat, lng, share, spread in CLUSTERS:
            acc += share
            if r <= acc:
                break
        alerts = rng.randint(0, 12)
        responded = rng.randint(0, alerts)
        accepted = rng.randint(0, responded)
        db.add(Donor(
            name=f"{first} {rng.choice(LAST)}",
            phone=f"{SYNTHETIC_PREFIX}{i:05d}",
            blood_group=rng.choices(groups, weights)[0],
            gender="F" if first in FEMALE else "M",
            dob=today - timedelta(days=rng.randint(19 * 365, 55 * 365)),
            weight_ok=True,
            lat=round(rng.gauss(lat, spread), 5),
            lng=round(rng.gauss(lng, spread), 5),
            location_label="Synthetic donor",
            language="hi" if rng.random() < 0.3 else "en",
            consent=True,
            night_ok=rng.random() < 0.25,
            last_donation_date=None if rng.random() < 0.4 else today - timedelta(days=rng.randint(10, 400)),
            alerts_sent=alerts, alerts_responded=responded, alerts_accepted=accepted,
            no_shows=rng.randint(0, 1) if accepted else 0,
            reply_hours=[rng.choice([9, 10, 13, 18, 19, 20, 21]) for _ in range(responded)],
            last_alerted_at=None if not alerts else utcnow() - timedelta(days=rng.randint(2, 90)),
            synthetic=True,
        ))
    return n


def reset_and_seed(db: Session, donors: int = 200) -> dict:
    """Wipe every table and re-seed. Rows are deleted rather than tables dropped, so open
    connections (live dashboards) are not blocked."""
    Base.metadata.create_all(engine)
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    banks = seed_blood_banks(db)
    ds = seed_donors(db, donors)
    db.flush()
    extras = seed_extras(db)
    db.commit()
    from .services import forecast
    forecast._cache.clear()
    return {"blood_banks": banks, "donors": ds, **extras}
