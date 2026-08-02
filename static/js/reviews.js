const reviewForm = document.getElementById('reviewForm');

reviewForm?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(reviewForm));
  const response = await apiFetch('/api/reviews', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  alert(data.message || data.error || 'Request processed');
  if (data.success) {
    window.location.reload();
  }
});

document.querySelectorAll('.reviewCommentForm').forEach((form) => {
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const reviewId = form.dataset.reviewId;
    const payload = Object.fromEntries(new FormData(form));
    const response = await apiFetch(`/api/reviews/${reviewId}/comments`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    alert(data.message || data.error || 'Request processed');
    if (data.success) {
      window.location.reload();
    }
  });
});
