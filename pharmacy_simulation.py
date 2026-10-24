"""
Pharmacy Simulation
-------------------
A console-based simulation of a small pharmacy.

Features:
  - Drug inventory with stock levels, prices and controlled-substance flags
  - Patient profiles with allergies and current medications
  - Prescription processing with safety checks:
        * stock availability
        * allergy check
        * drug-drug interaction check
        * refill tracking
  - Waiting queue of prescriptions
  - Restocking and low-stock alerts
  - Automatic "simulate a day" mode with random patients
  - End-of-day sales report

Run:  python pharmacy_simulation.py
"""

import random
from collections import deque
from datetime import datetime

LOW_STOCK_LEVEL = 20


# ---------------------------------------------------------------- data models
class Drug:
    def __init__(self, name, strength, stock, price, drug_class,
                 controlled=False, interacts_with=None):
        self.name = name
        self.strength = strength
        self.stock = stock
        self.price = price              # price per unit (tablet/capsule)
        self.drug_class = drug_class    # used for allergy checks
        self.controlled = controlled
        self.interacts_with = set(interacts_with or [])

    def __str__(self):
        flag = " [C]" if self.controlled else ""
        low = "  <-- LOW STOCK" if self.stock < LOW_STOCK_LEVEL else ""
        return (f"{self.name:<15}{self.strength:<9}{self.drug_class:<16}"
                f"{self.stock:>6}   ${self.price:>6.2f}{flag}{low}")


class Patient:
    def __init__(self, name, age, allergies=None, current_meds=None):
        self.name = name
        self.age = age
        self.allergies = set(allergies or [])       # drug classes
        self.current_meds = set(current_meds or [])  # drug names

    def __str__(self):
        allergies = ", ".join(self.allergies) or "None"
        meds = ", ".join(self.current_meds) or "None"
        return f"{self.name} (age {self.age}) | Allergies: {allergies} | Meds: {meds}"


class Prescription:
    _next_id = 1000

    def __init__(self, patient, drug_name, quantity, refills, doctor):
        self.rx_id = Prescription._next_id
        Prescription._next_id += 1
        self.patient = patient
        self.drug_name = drug_name
        self.quantity = quantity
        self.refills = refills
        self.doctor = doctor
        self.status = "Waiting"
        self.note = ""

    def __str__(self):
        return (f"Rx#{self.rx_id} | {self.patient.name:<14} | {self.drug_name:<13} "
                f"x{self.quantity:<4} | Refills: {self.refills} | Dr. {self.doctor} "
                f"| {self.status} {self.note}")


# ---------------------------------------------------------------- pharmacy
class Pharmacy:
    def __init__(self, name):
        self.name = name
        self.inventory = {}
        self.patients = {}
        self.queue = deque()
        self.history = []
        self.revenue = 0.0
        self._load_sample_data()

    # ---- setup
    def _load_sample_data(self):
        drugs = [
            Drug("Amoxicillin", "500mg", 200, 0.35, "Penicillin"),
            Drug("Ibuprofen", "400mg", 300, 0.10, "NSAID", interacts_with=["Warfarin", "Lisinopril"]),
            Drug("Warfarin", "5mg", 80, 0.45, "Anticoagulant", interacts_with=["Ibuprofen", "Aspirin"]),
            Drug("Aspirin", "81mg", 250, 0.05, "NSAID", interacts_with=["Warfarin"]),
            Drug("Lisinopril", "10mg", 150, 0.25, "ACE Inhibitor", interacts_with=["Ibuprofen"]),
            Drug("Metformin", "500mg", 180, 0.20, "Biguanide"),
            Drug("Atorvastatin", "20mg", 120, 0.60, "Statin"),
            Drug("Azithromycin", "250mg", 60, 1.20, "Macrolide"),
            Drug("Oxycodone", "5mg", 40, 1.50, "Opioid", controlled=True),
            Drug("Sertraline", "50mg", 15, 0.70, "SSRI"),
        ]
        for d in drugs:
            self.inventory[d.name.lower()] = d

        patients = [
            Patient("Alice Brown", 34, allergies=["Penicillin"]),
            Patient("Ben Carter", 67, current_meds=["Warfarin"]),
            Patient("Chloe Davis", 52, current_meds=["Lisinopril", "Metformin"]),
            Patient("Daniel Evans", 25),
            Patient("Emma Foster", 45, allergies=["Macrolide"]),
            Patient("Frank Green", 71, current_meds=["Atorvastatin"]),
        ]
        for p in patients:
            self.patients[p.name.lower()] = p

    # ---- lookups
    def find_drug(self, name):
        return self.inventory.get(name.strip().lower())

    def find_patient(self, name):
        return self.patients.get(name.strip().lower())

    # ---- workflow
    def receive_prescription(self, rx):
        self.queue.append(rx)
        print(f"  Received {rx.drug_name} for {rx.patient.name} (Rx#{rx.rx_id}).")

    def safety_check(self, rx, drug):
        """Return a list of problems; empty list means safe to dispense."""
        problems = []
        if drug.drug_class in rx.patient.allergies:
            problems.append(f"ALLERGY: patient allergic to {drug.drug_class}")
        clashes = drug.interacts_with & rx.patient.current_meds
        if clashes:
            problems.append(f"INTERACTION with {', '.join(clashes)}")
        if drug.stock < rx.quantity:
            problems.append(f"OUT OF STOCK (have {drug.stock}, need {rx.quantity})")
        if drug.controlled and rx.quantity > 30:
            problems.append("CONTROLLED: quantity over 30 needs prescriber approval")
        return problems

    def process_next(self):
        if not self.queue:
            print("  Queue is empty.")
            return
        rx = self.queue.popleft()
        drug = self.find_drug(rx.drug_name)

        if drug is None:
            rx.status, rx.note = "Rejected", "(drug not carried)"
        else:
            problems = self.safety_check(rx, drug)
            if problems:
                rx.status, rx.note = "On hold", "(" + "; ".join(problems) + ")"
            else:
                drug.stock -= rx.quantity
                cost = rx.quantity * drug.price
                self.revenue += cost
                rx.patient.current_meds.add(drug.name)
                rx.status, rx.note = "Dispensed", f"(${cost:.2f})"
                if drug.stock < LOW_STOCK_LEVEL:
                    print(f"  ! Low stock alert: {drug.name} has {drug.stock} left")

        self.history.append(rx)
        print("  " + str(rx))

    def process_all(self):
        while self.queue:
            self.process_next()

    def restock(self, drug_name, amount):
        drug = self.find_drug(drug_name)
        if drug is None:
            print("  Drug not found.")
            return
        drug.stock += amount
        print(f"  Restocked {drug.name}: now {drug.stock} units.")

    def auto_restock_low(self, amount=100):
        for drug in self.inventory.values():
            if drug.stock < LOW_STOCK_LEVEL:
                self.restock(drug.name, amount)

    # ---- displays
    def show_inventory(self):
        print(f"\n  {'Drug':<15}{'Strength':<9}{'Class':<16}{'Stock':>6}   {'Price':>7}")
        print("  " + "-" * 62)
        for drug in self.inventory.values():
            print("  " + str(drug))

    def show_patients(self):
        for p in self.patients.values():
            print("  " + str(p))

    def show_queue(self):
        if not self.queue:
            print("  Queue is empty.")
        for rx in self.queue:
            print("  " + str(rx))

    def report(self):
        counts = {"Dispensed": 0, "On hold": 0, "Rejected": 0}
        for rx in self.history:
            counts[rx.status] = counts.get(rx.status, 0) + 1
        print(f"\n  ===== {self.name} Daily Report ({datetime.now():%Y-%m-%d}) =====")
        print(f"  Prescriptions handled : {len(self.history)}")
        for status, n in counts.items():
            print(f"    {status:<20}: {n}")
        print(f"  Waiting in queue      : {len(self.queue)}")
        print(f"  Total revenue         : ${self.revenue:.2f}")
        low = [d.name for d in self.inventory.values() if d.stock < LOW_STOCK_LEVEL]
        print(f"  Low-stock items       : {', '.join(low) or 'None'}")

    # ---- automatic simulation
    def simulate_day(self, num_customers=10, seed=None):
        rng = random.Random(seed)
        doctors = ["Smith", "Patel", "Nguyen", "Garcia", "Johnson"]
        print(f"\n  --- Simulating a day with {num_customers} prescriptions ---")
        for _ in range(num_customers):
            patient = rng.choice(list(self.patients.values()))
            drug = rng.choice(list(self.inventory.values()))
            qty = rng.choice([10, 14, 20, 30, 60, 90])
            rx = Prescription(patient, drug.name, qty, rng.randint(0, 3), rng.choice(doctors))
            self.receive_prescription(rx)
        print("\n  --- Pharmacist processing queue ---")
        self.process_all()
        self.report()


# ---------------------------------------------------------------- user input helpers
def ask_int(prompt, minimum=0):
    while True:
        try:
            value = int(input(prompt))
            if value >= minimum:
                return value
        except ValueError:
            pass
        print(f"  Please enter a whole number >= {minimum}.")


def new_prescription(pharmacy):
    name = input("  Patient name: ")
    patient = pharmacy.find_patient(name)
    if patient is None:
        print("  New patient - creating profile.")
        age = ask_int("  Age: ", 0)
        allergies = input("  Allergies (drug classes, comma-separated, blank for none): ")
        meds = input("  Current medications (comma-separated, blank for none): ")
        patient = Patient(
            name.strip().title(), age,
            [a.strip() for a in allergies.split(",") if a.strip()],
            [m.strip().title() for m in meds.split(",") if m.strip()],
        )
        pharmacy.patients[patient.name.lower()] = patient
    drug = input("  Drug name: ").strip().title()
    qty = ask_int("  Quantity: ", 1)
    refills = ask_int("  Refills: ", 0)
    doctor = input("  Prescribing doctor: ").strip() or "Unknown"
    pharmacy.receive_prescription(Prescription(patient, drug, qty, refills, doctor))


# ---------------------------------------------------------------- main menu
def main():
    pharmacy = Pharmacy("Main Street Pharmacy")
    menu = """
==================== PHARMACY SIMULATION ====================
 1. View inventory          6. Process all prescriptions
 2. View patients           7. Restock a drug
 3. New prescription        8. Auto-restock low items
 4. View waiting queue      9. Simulate a full day
 5. Process next Rx        10. Daily report
 0. Exit
=============================================================="""
    while True:
        print(menu)
        choice = input("Choose an option: ").strip()
        if choice == "1":
            pharmacy.show_inventory()
        elif choice == "2":
            pharmacy.show_patients()
        elif choice == "3":
            new_prescription(pharmacy)
        elif choice == "4":
            pharmacy.show_queue()
        elif choice == "5":
            pharmacy.process_next()
        elif choice == "6":
            pharmacy.process_all()
        elif choice == "7":
            name = input("  Drug name: ")
            pharmacy.restock(name, ask_int("  Amount to add: ", 1))
        elif choice == "8":
            pharmacy.auto_restock_low()
        elif choice == "9":
            pharmacy.simulate_day(ask_int("  How many prescriptions? ", 1))
        elif choice == "10":
            pharmacy.report()
        elif choice == "0":
            print("Closing the pharmacy. Goodbye!")
            break
        else:
            print("  Invalid choice, try again.")


if __name__ == "__main__":
    main()
