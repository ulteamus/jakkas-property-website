def calculate_emi(principal, annual_rate, tenure_months):
    """Calculate monthly EMI for a home loan."""
    if tenure_months <= 0 or principal <= 0:
        return {
            "emi": 0,
            "total_payment": 0,
            "total_interest": 0,
        }

    monthly_rate = annual_rate / 12 / 100
    if monthly_rate == 0:
        emi = principal / tenure_months
    else:
        emi = principal * monthly_rate * (1 + monthly_rate) ** tenure_months
        emi /= (1 + monthly_rate) ** tenure_months - 1

    total_payment = emi * tenure_months
    total_interest = total_payment - principal

    return {
        "emi": round(emi, 2),
        "total_payment": round(total_payment, 2),
        "total_interest": round(total_interest, 2),
        "principal": round(principal, 2),
        "annual_rate": annual_rate,
        "tenure_months": tenure_months,
        "tenure_years": round(tenure_months / 12, 1),
    }
