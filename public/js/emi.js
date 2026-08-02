const emiForm = document.getElementById('emiForm');

emiForm?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const principal = +document.getElementById('principal').value;
  const annual_rate = +document.getElementById('annual_rate').value;
  const years = +document.getElementById('tenure_years').value;

  const res = await apiFetch('/api/emi', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      principal,
      annual_rate,
      tenure_months: years * 12,
    }),
  });

  const d = await res.json();
  if (!d.success) return;

  document.getElementById('emiValue').textContent = formatINR(d.emi);
  document.getElementById('emiBreakdown').innerHTML = `
    <li>Loan amount: ${formatINR(d.principal)}</li>
    <li>Interest rate: ${d.annual_rate}% p.a.</li>
    <li>Tenure: ${d.tenure_years} years (${d.tenure_months} months)</li>
    <li>Total payment: ${formatINR(d.total_payment)}</li>
    <li>Total interest: ${formatINR(d.total_interest)}</li>
  `;
});

// Calculate on load
emiForm?.requestSubmit();
