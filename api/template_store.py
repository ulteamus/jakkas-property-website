"""Auto-generated Jinja templates for Vercel serverless runtime."""
from jinja2 import DictLoader

TEMPLATES = {
    "404.html": """{% extends "base.html" %}
{% block title %}Not Found{% endblock %}
{% block content %}
<div class="container section text-center">
  <h1>404</h1>
  <p>Property not found.</p>
  <a href="{{ url_for('main.index') }}" class="btn btn-primary">Go Home</a>
</div>
{% endblock %}
""",
    "admin/activity_logs.html": """{% extends "admin/base.html" %}
{% block title %}Activity Logs{% endblock %}
{% block page_heading %}Activity Logs{% endblock %}
{% block page_subheading %}Chronological audit trail of employee actions across admin workflows.{% endblock %}
{% block content %}
<section class="admin-section-card">
  <form method="GET" class="row g-3 align-items-end">
    <div class="col-md-3">
      <label>Start Date</label>
      <input type="date" class="form-control" name="start_date" value="{{ start_date }}">
    </div>
    <div class="col-md-3">
      <label>End Date</label>
      <input type="date" class="form-control" name="end_date" value="{{ end_date }}">
    </div>
    <div class="col-md-3">
      <label>Admin</label>
      <select class="form-select" name="admin_id">
        <option value="">All Admins</option>
        {% for admin in admins %}
        <option value="{{ admin.id }}" {% if selected_admin_id == admin.id %}selected{% endif %}>
          {{ admin.full_name or admin.username }} ({{ admin.role|replace('_', ' ')|title }})
        </option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <label>Action Key</label>
      <input class="form-control" name="action_key" value="{{ selected_action }}" placeholder="property_added">
    </div>
    <div class="col-12 d-flex gap-2">
      <button class="btn btn-jk-accent">Apply Filters</button>
      <a class="btn btn-outline-secondary" href="{{ url_for('admin.activity_logs_dashboard') }}">Reset</a>
    </div>
  </form>
</section>

<section class="admin-table-wrap table-responsive">
  <table class="table align-middle">
    <thead>
      <tr>
        <th>Time</th>
        <th>Admin</th>
        <th>Action</th>
        <th>Entity</th>
        <th>Metadata</th>
      </tr>
    </thead>
    <tbody>
      {% for log in logs %}
      <tr>
        <td>{{ log.created_at }}</td>
        <td>{{ log.admin_display }}</td>
        <td>
          <div class="fw-semibold">{{ log.action_label }}</div>
          <div class="small text-muted">{{ log.action_key }}</div>
        </td>
        <td>
          {% if log.entity_type %}
          {{ log.entity_type }}{% if log.entity_id %} #{{ log.entity_id }}{% endif %}
          {% else %}
          -
          {% endif %}
        </td>
        <td><code class="small">{{ log.meta }}</code></td>
      </tr>
      {% else %}
      <tr>
        <td colspan="5" class="text-center text-muted py-4">No activity logs found.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</section>
{% endblock %}
""",
    "admin/admin_users.html": """{% extends "admin/base.html" %}
{% block title %}Employee Permissions{% endblock %}
{% block page_heading %}Employee Permission Management{% endblock %}
{% block page_subheading %}Create employee admins, assign role presets, and control granular access with OTP-secured updates.{% endblock %}
{% block page_actions %}
<span class="badge bg-secondary align-self-center">{{ admins|length }} accounts</span>
{% endblock %}
{% block content %}
{% if setup_payload %}
<section class="admin-section-card mb-3">
  <div class="admin-section-heading">
    <h5>Google Authenticator Setup: {{ setup_payload.username }}</h5>
  </div>
  <div class="row g-3 align-items-center">
    <div class="col-md-4 text-center">
      <img src="{{ setup_payload.qr_url }}" alt="TOTP QR Code" class="img-fluid rounded border" style="max-width: 220px;">
    </div>
    <div class="col-md-8">
      <p class="mb-2"><strong>Secret:</strong> <code>{{ setup_payload.secret }}</code></p>
      <p class="small text-muted mb-2">Scan this QR in Google Authenticator (or compatible app), then verify at next login.</p>
      <div class="small text-muted text-break">{{ setup_payload.otpauth_uri }}</div>
    </div>
  </div>
</section>
{% endif %}

<section class="admin-section-card mb-3">
  <div class="admin-section-heading">
    <h5>Create Employee Admin</h5>
  </div>
  <form method="POST" action="{{ url_for('admin.create_admin_user') }}" class="row g-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="col-md-3">
      <label class="form-label">Username *</label>
      <input class="form-control" name="username" required>
    </div>
    <div class="col-md-3">
      <label class="form-label">Email</label>
      <input type="email" class="form-control" name="email" placeholder="Optional">
    </div>
    <div class="col-md-3">
      <label class="form-label">Full Name</label>
      <input class="form-control" name="full_name">
    </div>
    <div class="col-md-3">
      <label class="form-label">Phone</label>
      <input class="form-control" name="phone" placeholder="+91xxxxxxxxxx">
    </div>
    <div class="col-md-3">
      <label class="form-label">Password *</label>
      <input type="password" class="form-control" name="password" minlength="6" required>
    </div>
    <div class="col-md-3">
      <label class="form-label">Role Preset *</label>
      <select class="form-select" name="role" required>
        {% for opt in role_options %}
        <option value="{{ opt.value }}">{{ opt.title }}</option>
        {% else %}
        {% for role in role_keys %}
        <option value="{{ role }}">{{ role|replace('_', ' ')|title }}</option>
        {% endfor %}
        <option value="broker">Broker</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-12">
      <label class="form-label">Granular Permissions (optional override)</label>      <div class="row row-cols-1 row-cols-md-4 g-2">
        {% for key in permission_keys %}
        <div class="col">
          <label class="form-check border rounded p-2 d-flex align-items-center gap-2">
            <input class="form-check-input mt-0" type="checkbox" name="permissions" value="{{ key }}">
            <span class="small">{{ key }}</span>
          </label>
        </div>
        {% endfor %}
      </div>
      <p class="small text-muted mt-2 mb-0">If no permission is checked, default role preset permissions are applied automatically.</p>
    </div>
    <div class="col-12">
      <button class="btn btn-jk-accent">Create Employee Admin</button>
    </div>
  </form>
</section>

<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Employee Accounts</h5>
  </div>
  <div class="admin-table-wrap table-responsive">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>User</th>
          <th>Role</th>
          <th>Status</th>
          <th>Verification</th>
          <th>Permissions</th>
          <th style="min-width: 290px;">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for admin_row in admins %}
        <tr>
          <td>
            <div class="fw-semibold">{{ admin_row.full_name or admin_row.username }}</div>
            <div class="small text-muted">{{ admin_row.username }} • {{ admin_row.email }}</div>
            <div class="small text-muted">{{ admin_row.phone or "No phone configured" }}</div>
          </td>
          <td>
            <span class="admin-status-pill status-pending">{{ admin_row.role|replace('_', ' ')|title }}</span>
          </td>
          <td>
            {% if admin_row.is_active %}
            <span class="admin-status-pill status-approved">Active</span>
            {% else %}
            <span class="admin-status-pill status-rejected">Inactive</span>
            {% endif %}
          </td>
          <td class="small">{{ admin_row.verification_summary }}</td>
          <td class="small">{{ admin_row.permission_summary }}</td>
          <td class="text-nowrap">
            <form method="POST" action="{{ url_for('admin.toggle_admin_user', admin_id=admin_row.id) }}" class="d-inline">
              <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
              <input type="hidden" name="is_active" value="{{ 0 if admin_row.is_active else 1 }}">
              <button class="btn btn-sm btn-outline-secondary">{{ "Disable" if admin_row.is_active else "Enable" }}</button>
            </form>
            <a href="{{ url_for('admin.admin_users', edit=admin_row.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
            {% if not admin_row.is_super_admin or admins|selectattr('is_super_admin')|list|length > 1 %}
            <form method="POST" action="{{ url_for('admin.delete_admin_user', admin_id=admin_row.id) }}" class="d-inline" onsubmit="return confirm('Deactivate this account?')">
              <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
              <button class="btn btn-sm btn-outline-danger">Deactivate</button>
            </form>
            {% endif %}
          </td>
        </tr>
        {% if edit_admin_id == admin_row.id %}
        <tr>
          <td colspan="6">
            <div class="border rounded p-3 bg-light-subtle">
              <h6 class="mb-3">Edit: {{ admin_row.username }}</h6>
              <form method="POST" action="{{ url_for('admin.update_admin_user', admin_id=admin_row.id) }}" class="row g-3">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <div class="col-md-3">
                  <label class="form-label">Email</label>
                  <input type="email" class="form-control" name="email" value="{{ admin_row.email }}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Full Name</label>
                  <input class="form-control" name="full_name" value="{{ admin_row.full_name }}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Phone</label>
                  <input class="form-control" name="phone" value="{{ admin_row.phone or '' }}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Reset Password</label>
                  <input type="password" class="form-control" name="password" minlength="6" placeholder="Leave blank to keep">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Role Preset</label>
                  <select class="form-select" name="role" required>
                    {% for opt in role_options %}
                    <option value="{{ opt.value }}" {% if admin_row.role == opt.value %}selected{% endif %}>{{ opt.title }}</option>
                    {% else %}
                    {% for role in role_keys %}
                    <option value="{{ role }}" {% if admin_row.role == role %}selected{% endif %}>{{ role|replace('_', ' ')|title }}</option>
                    {% endfor %}
                    <option value="broker" {% if admin_row.role == 'broker' %}selected{% endif %}>Broker</option>
                    {% endfor %}
                  </select>
                </div>
                <div class="col-md-9 d-flex align-items-end gap-4">
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="is_active" id="active{{ admin_row.id }}" value="1" {% if admin_row.is_active %}checked{% endif %}>
                    <label class="form-check-label" for="active{{ admin_row.id }}">Active</label>
                  </div>
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="require_otp" id="req{{ admin_row.id }}" value="1" {% if admin_row.require_otp %}checked{% endif %}>
                    <label class="form-check-label" for="req{{ admin_row.id }}">Require OTP</label>
                  </div>
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="mobile_otp_enabled" id="mob{{ admin_row.id }}" value="1" {% if admin_row.mobile_otp_enabled %}checked{% endif %}>
                    <label class="form-check-label" for="mob{{ admin_row.id }}">Enable Mobile OTP</label>
                  </div>
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="phone_verified" id="pv{{ admin_row.id }}" value="1" {% if admin_row.phone_verified %}checked{% endif %}>
                    <label class="form-check-label" for="pv{{ admin_row.id }}">Phone Verified</label>
                  </div>
                </div>
                <div class="col-12">
                  <label class="form-label">Permission Matrix</label>
                  <div class="row row-cols-1 row-cols-md-4 g-2">
                    {% for key in permission_keys %}
                    <div class="col">
                      <label class="form-check border rounded p-2 d-flex align-items-center gap-2">
                        <input class="form-check-input mt-0" type="checkbox" name="permissions" value="{{ key }}" {% if admin_row.has_permission(key) %}checked{% endif %}>
                        <span class="small">{{ key }}</span>
                      </label>
                    </div>
                    {% endfor %}
                  </div>
                </div>
                <div class="col-12 d-flex gap-2">
                  <button class="btn btn-jk-accent">Save Employee Access</button>
                  <a class="btn btn-outline-secondary" href="{{ url_for('admin.admin_users') }}">Cancel</a>
                </div>
              </form>
              <hr class="my-3">
              <div class="d-flex flex-wrap align-items-center gap-2">
                <form method="POST" action="{{ url_for('admin.setup_admin_totp', admin_id=admin_row.id) }}">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <button class="btn btn-sm btn-outline-dark">Setup TOTP</button>
                </form>
                <form method="POST" action="{{ url_for('admin.setup_admin_totp', admin_id=admin_row.id) }}">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <input type="hidden" name="regenerate" value="1">
                  <button class="btn btn-sm btn-outline-secondary">Regenerate TOTP Secret</button>
                </form>
                <form method="POST" action="{{ url_for('admin.disable_admin_totp', admin_id=admin_row.id) }}" onsubmit="return confirm('Disable Google Authenticator for this account?')">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <button class="btn btn-sm btn-outline-danger">Disable TOTP</button>
                </form>
                {% if setup_payload and setup_payload.admin_id == admin_row.id %}
                <a class="btn btn-sm btn-outline-primary" href="#totp-setup-anchor">View Latest Setup QR</a>
                {% endif %}
              </div>
            </div>
          </td>
        </tr>
        {% endif %}
        {% else %}
        <tr>
          <td colspan="6" class="text-center text-muted py-4">No employee admin accounts found.</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section class="admin-section-card mt-3">
  <div class="admin-section-heading">
    <h5>Default Role Permission Presets</h5>
  </div>
  <div class="row g-3">
    {% for opt in role_options %}
    <div class="col-md-6 col-lg-3">
      <div class="border rounded p-3 h-100">
        <h6 class="mb-2">{{ opt.title }}</h6>
        <ul class="small mb-0">
          {% for key in opt.permissions %}
          <li>{{ key }}</li>
          {% else %}
          <li>No default permissions</li>
          {% endfor %}
        </ul>
      </div>
    </div>
    {% else %}
    {% for role in role_keys %}
    <div class="col-md-6 col-lg-3">
      <div class="border rounded p-3 h-100">
        <h6 class="mb-2">{{ role|replace('_', ' ')|title }}</h6>
        <ul class="small mb-0">
          {% for key in role_presets.get(role, []) %}
          <li>{{ key }}</li>
          {% else %}
          <li>No default permissions</li>
          {% endfor %}
        </ul>
      </div>
    </div>
    {% endfor %}
    <div class="col-md-6 col-lg-3">
      <div class="border rounded p-3 h-100">
        <h6 class="mb-2">Broker</h6>
        <ul class="small mb-0">
          <li>manage_properties</li>
          <li>manage_leads</li>
          <li>manage_inquiries</li>
        </ul>
      </div>
    </div>
    {% endfor %}
  </div>
</section>
{% if setup_payload %}
<div id="totp-setup-anchor"></div>
{% endif %}
{% endblock %}
""",
    "admin/analytics.html": """{% extends "admin/base.html" %}
{% block title %}Analytics{% endblock %}
{% block page_heading %}Demand Analytics{% endblock %}
{% block page_subheading %}Understand market movement, top areas, and listing performance with clearer visual hierarchy.{% endblock %}
{% block content %}
<section class="admin-section-card">
  <div class="kpi-top">
    <p class="kpi-label">Conversion Rate</p>
    <span class="kpi-icon"><i class="bi bi-activity"></i></span>
  </div>
  <h3 class="kpi-value">{{ conversion }}%</h3>
  <p class="kpi-meta">Overall inquiry-to-lead conversion performance.</p>
</section>

<div class="row g-4">
  <div class="col-md-6">
    <section class="admin-section-card h-100 p-0 overflow-hidden">
      <div class="admin-section-heading p-3 pb-0">
        <h5>Trending Areas</h5>
      </div>
      <div class="admin-table-wrap table-responsive border-0 rounded-0 shadow-none">
        <table class="table table-sm align-middle">
          <thead>
            <tr><th>Area</th><th>Demand Score</th><th>Searches</th></tr>
          </thead>
          <tbody>
            {% for a in trending %}
            <tr><td>{{ a.area_name }}</td><td>{{ a.demand_score }}</td><td>{{ a.search_count }}</td></tr>
            {% else %}
            <tr><td colspan="3" class="text-center text-muted py-4">No trend data available.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>
  </div>
  <div class="col-md-6">
    <section class="admin-section-card h-100 p-0 overflow-hidden">
      <div class="admin-section-heading p-3 pb-0">
        <h5>By Property Type</h5>
      </div>
      <div class="admin-table-wrap table-responsive border-0 rounded-0 shadow-none">
        <table class="table table-sm align-middle">
          <thead>
            <tr><th>Type</th><th>Count</th><th>Avg Price</th></tr>
          </thead>
          <tbody>
            {% for t in by_type %}
            <tr><td>{{ t.property_type }}</td><td>{{ t.cnt }}</td><td>₹{{ "{:,.0f}".format(t.avg_price or 0) }}</td></tr>
            {% else %}
            <tr><td colspan="3" class="text-center text-muted py-4">No type data available.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </section>
  </div>
</div>

<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Most Viewed Properties</h5>
  </div>
  <ul class="list-group">
    {% for p in top %}
    <li class="list-group-item d-flex justify-content-between">{{ p.property_name }} <span class="badge bg-secondary">{{ p.view_count }} views</span></li>
    {% else %}
    <li class="list-group-item text-muted">No property view data available.</li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
""",
    "admin/base.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}Admin{% endblock %} - {{ company_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/admin.css') }}" rel="stylesheet">
</head>
<body class="admin-theme">
{% set endpoint = request.endpoint or '' %}
<div class="admin-shell">
  <aside class="admin-sidebar offcanvas-lg offcanvas-start" tabindex="-1" id="adminSidebar" aria-labelledby="adminSidebarLabel">
    <div class="offcanvas-header d-lg-none">
      <h5 class="offcanvas-title text-white" id="adminSidebarLabel">Navigation</h5>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="offcanvas" aria-label="Close"></button>
    </div>
    <div class="offcanvas-body">
      <div class="admin-brand-wrap">
        <span class="admin-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" class="jk-logo jk-logo-mark" alt="{{ company_name }}">
        </span>
        <div class="admin-brand-copy">
          <p class="admin-brand-title">{{ company_name }}</p>
          <small>Admin Command Center</small>
        </div>
      </div>
      <nav class="admin-nav">
        <a href="{{ url_for('admin.dashboard') }}" class="admin-nav-link {% if endpoint == 'admin.dashboard' %}active{% endif %}">
          <i class="bi bi-speedometer2"></i>
          <span>Dashboard</span>
        </a>
        {% if current_user.has_permission('manage_properties') %}
        <a href="{{ url_for('admin.properties') }}" class="admin-nav-link {% if endpoint == 'admin.properties' %}active{% endif %}">
          <i class="bi bi-building"></i>
          <span>Properties</span>
        </a>
        {% endif %}
        {% if current_user.has_permission('manage_submissions') %}
        <a href="{{ url_for('admin.sell_properties') }}" class="admin-nav-link {% if endpoint in ['admin.sell_properties', 'admin.edit_sell_property', 'admin.print_sell_properties', 'admin.submissions_redirect'] %}active{% endif %}">
          <i class="bi bi-house-add"></i>
          <span>Sell Properties</span>
        </a>
        {% endif %}
        {% if current_user.has_permission('manage_inquiries') %}
        <a href="{{ url_for('admin.inquiries') }}" class="admin-nav-link {% if endpoint in ['admin.inquiries', 'admin.inquiry_detail', 'admin.update_inquiry', 'admin.print_inquiries'] %}active{% endif %}">
          <i class="bi bi-envelope"></i>
          <span>Inquiries</span>
        </a>
        {% endif %}
        {% if current_user.has_permission('manage_customer_visits') %}
        <a href="{{ url_for('admin.customer_visits') }}" class="admin-nav-link {% if endpoint in ['admin.customer_visits', 'admin.print_customer_visit', 'admin.customer_visit_pdf'] %}active{% endif %}">
          <i class="bi bi-clipboard2-check"></i>
          <span>Customer Visits</span>
        </a>
        {% endif %}
        {% if current_user.has_permission('manage_reviews') %}
        <a href="{{ url_for('admin.reviews') }}" class="admin-nav-link {% if endpoint == 'admin.reviews' %}active{% endif %}">
          <i class="bi bi-chat-left-text"></i>
          <span>Reviews</span>
        </a>
        {% endif %}
        {% if current_user.has_permission('view_analytics') %}
        <a href="{{ url_for('admin.analytics') }}" class="admin-nav-link {% if endpoint == 'admin.analytics' %}active{% endif %}">
          <i class="bi bi-graph-up"></i>
          <span>Analytics</span>
        </a>
        {% endif %}
        {% if current_user.is_super_admin %}
        <a href="{{ url_for('admin.activity_logs_dashboard') }}" class="admin-nav-link {% if endpoint == 'admin.activity_logs_dashboard' %}active{% endif %}">
          <i class="bi bi-clock-history"></i>
          <span>Activity Logs</span>
        </a>
        <a href="{{ url_for('admin.admin_utilities') }}" class="admin-nav-link {% if endpoint in ['admin.admin_utilities', 'admin.flush_mock_data'] %}active{% endif %}">
          <i class="bi bi-sliders"></i>
          <span>Utilities</span>
        </a>
        <a href="{{ url_for('admin.admin_users') }}" class="admin-nav-link {% if endpoint in ['admin.admin_users', 'admin.create_admin_user', 'admin.update_admin_user', 'admin.toggle_admin_user', 'admin.delete_admin_user', 'admin.setup_admin_totp', 'admin.disable_admin_totp'] %}active{% endif %}">
          <i class="bi bi-person-gear"></i>
          <span>Employees</span>
        </a>
        {% endif %}
      </nav>
      <div class="admin-sidebar-footer">
        {% if current_user.has_permission('manage_properties') %}
        <a href="{{ url_for('admin.property_form') }}" class="admin-nav-link {% if endpoint == 'admin.property_form' %}active{% endif %}">
          <i class="bi bi-plus-circle"></i>
          <span>Add Property</span>
        </a>
        {% endif %}
        <a href="{{ url_for('public.home') }}" target="_blank" class="admin-nav-link">
          <i class="bi bi-globe"></i>
          <span>View Website</span>
        </a>
        <a href="{{ url_for('auth.admin_logout') }}" class="admin-nav-link">
          <i class="bi bi-box-arrow-right"></i>
          <span>Logout</span>
        </a>
      </div>
    </div>
  </aside>
  <main class="admin-main">
    <header class="admin-page-header">
      <div class="d-flex align-items-start gap-2">
        <button class="btn admin-mobile-toggle d-lg-none" type="button" data-bs-toggle="offcanvas" data-bs-target="#adminSidebar" aria-controls="adminSidebar" aria-label="Open navigation">
          <i class="bi bi-list"></i>
        </button>
        <div>
          <span class="admin-page-kicker">Admin Workspace</span>
          <h1 class="admin-page-title">{% block page_heading %}Control Center{% endblock %}</h1>
          <p class="admin-page-subtitle">{% block page_subheading %}Manage operations, listings, and lead pipeline from one premium dashboard.{% endblock %}</p>
        </div>
      </div>
      <div class="admin-header-actions">
        {% block page_actions %}{% endblock %}
      </div>
    </header>

    <section class="admin-flash-stack">
      {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
      {% endfor %}
      {% endwith %}
    </section>

    <section class="admin-content">
      {% block content %}{% endblock %}
    </section>
  </main>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
{% block extra_js %}{% endblock %}
</body>
</html>
""",
    "admin/customer_visits.html": """{% extends "admin/base.html" %}
{% block title %}Customer Visits{% endblock %}
{% block page_heading %}Customer Visit Form{% endblock %}
{% block page_subheading %}Capture visit records with linked properties and signature areas.{% endblock %}
{% block content %}
<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Create Customer Visit Record</h5>
  </div>
  <form method="POST" class="row g-3" id="customerVisitForm">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="col-md-3">
      <label>Visit Date *</label>
      <input type="date" class="form-control" name="visit_date" required>
    </div>
    <div class="col-md-5">
      <label>Client Name *</label>
      <input class="form-control" name="client_name" required>
    </div>
    <div class="col-md-4">
      <label>Client Contact *</label>
      <input class="form-control" name="client_contact" required>
    </div>
    <div class="col-md-6">
      <label>Client Address *</label>
      <textarea class="form-control" name="client_address" rows="2" required></textarea>
    </div>
    <div class="col-md-6">
      <label>Client Requirement *</label>
      <textarea class="form-control" name="client_requirement" rows="2" required></textarea>
    </div>
    <div class="col-12">
      <label>Visited Properties *</label>
      <select class="form-select" id="visitPropertySelect">
        <option value="">Add a property…</option>
        {% for property in properties %}
        <option value="{{ property.id }}">#{{ property.id }} - {{ property.property_name }} ({{ property.area_name }})</option>
        {% endfor %}
      </select>
      <div id="visitPropertyTags" class="d-flex flex-wrap gap-2 mt-2" aria-live="polite"></div>
      <div id="visitPropertyIds"></div>
      <div class="form-text">Select one or more properties. Click X on a tag to remove it.</div>
    </div>
    <div class="col-md-4">
      <label>Executive Name *</label>
      <input class="form-control" name="executive_name" required>
    </div>
    <div class="col-md-4">
      <label>Executive Contact *</label>
      <input class="form-control" name="executive_contact" required>
    </div>
    <div class="col-md-4">
      <label>Executive Address *</label>
      <input class="form-control" name="executive_address" required>
    </div>

    <div class="col-md-6">
      <label>Customer Signature Label</label>
      <input class="form-control mb-2" name="customer_signature_label" placeholder="Signed by customer">
      <canvas id="customerSignatureCanvas" class="signature-canvas border rounded w-100" height="130"></canvas>
      <input type="hidden" name="customer_signature_data" id="customerSignatureData">
      <button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="clearCustomerSignature">Clear Customer Signature</button>
    </div>
    <div class="col-md-6">
      <label>Executive Signature Label</label>
      <input class="form-control mb-2" name="executive_signature_label" placeholder="Signed by executive">
      <canvas id="executiveSignatureCanvas" class="signature-canvas border rounded w-100" height="130"></canvas>
      <input type="hidden" name="executive_signature_data" id="executiveSignatureData">
      <button type="button" class="btn btn-sm btn-outline-secondary mt-2" id="clearExecutiveSignature">Clear Executive Signature</button>
    </div>

    <div class="col-12">
      <button class="btn btn-jk-accent">Save Customer Visit Form</button>
    </div>
  </form>
</section>

<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Visit Records</h5>
    <form method="GET" class="row g-2">
      <div class="col-auto"><input type="date" class="form-control form-control-sm" name="start_date" value="{{ start_date }}"></div>
      <div class="col-auto"><input type="date" class="form-control form-control-sm" name="end_date" value="{{ end_date }}"></div>
      <div class="col-auto"><button class="btn btn-sm btn-outline-secondary">Filter by Date</button></div>
      <div class="col-auto"><a class="btn btn-sm btn-outline-dark" href="{{ url_for('admin.customer_visits') }}">Clear</a></div>
    </form>
  </div>
  <div class="admin-table-wrap table-responsive">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>Date</th>
          <th>Client</th>
          <th>Properties</th>
          <th>Executive</th>
          <th>Requirement</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for visit in visits %}
        <tr>
          <td>{{ visit.visit_date }}</td>
          <td>
            <div class="fw-semibold">{{ visit.client_name }}</div>
            <div class="small text-muted">{{ visit.client_contact }}</div>
          </td>
          <td>{{ visit.property_names_display or visit.property_name or ('Property #' ~ visit.property_id) }}</td>
          <td>
            <div>{{ visit.executive_name or '-' }}</div>
            <div class="small text-muted">{{ visit.executive_contact or '-' }}</div>
          </td>
          <td>{{ visit.client_requirement or '-' }}</td>
          <td class="text-nowrap">
            <a class="btn btn-sm btn-outline-secondary" target="_blank" href="{{ url_for('admin.print_customer_visit', visit_id=visit.id) }}">Print</a>
            <a class="btn btn-sm btn-outline-dark" href="{{ url_for('admin.customer_visit_pdf', visit_id=visit.id) }}">PDF</a>
            <form method="POST" action="{{ url_for('admin.delete_customer_visit', visit_id=visit.id) }}" class="d-inline" onsubmit="return confirm('Delete this visit record?');">
              <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
              <button class="btn btn-sm btn-outline-danger">Delete</button>
            </form>
          </td>
        </tr>
        {% else %}
        <tr>
          <td colspan="6" class="text-center text-muted py-4">No visit forms available.</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
{% block extra_js %}
<script>
  (function () {
    const select = document.getElementById('visitPropertySelect');
    const tags = document.getElementById('visitPropertyTags');
    const idsHost = document.getElementById('visitPropertyIds');
    const selected = new Map();

    function render() {
      tags.innerHTML = '';
      idsHost.innerHTML = '';
      selected.forEach((label, id) => {
        const pill = document.createElement('span');
        pill.className = 'badge text-bg-light border d-inline-flex align-items-center gap-2 px-2 py-2';
        pill.innerHTML = `<span>${label}</span>`;
        const x = document.createElement('button');
        x.type = 'button';
        x.className = 'btn btn-sm btn-link text-danger p-0';
        x.textContent = '×';
        x.addEventListener('click', () => { selected.delete(id); render(); });
        pill.appendChild(x);
        tags.appendChild(pill);
        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'property_ids';
        hidden.value = id;
        idsHost.appendChild(hidden);
      });
    }

    select?.addEventListener('change', () => {
      const id = select.value;
      const label = select.options[select.selectedIndex]?.text || id;
      if (id) selected.set(id, label);
      select.value = '';
      render();
    });

    document.getElementById('customerVisitForm')?.addEventListener('submit', (e) => {
      if (!selected.size) {
        e.preventDefault();
        alert('Please select at least one property.');
      }
    });
  })();

  function setupSignaturePad(canvasId, outputId, clearButtonId) {
    const canvas = document.getElementById(canvasId);
    const output = document.getElementById(outputId);
    const clearButton = document.getElementById(clearButtonId);
    if (!canvas || !output || !clearButton) return;

    canvas.width = canvas.offsetWidth;
    const ctx = canvas.getContext("2d");
    let drawing = false;

    function getPos(event) {
      const rect = canvas.getBoundingClientRect();
      const source = event.touches ? event.touches[0] : event;
      return {
        x: source.clientX - rect.left,
        y: source.clientY - rect.top,
      };
    }

    function start(event) {
      drawing = true;
      const pos = getPos(event);
      ctx.beginPath();
      ctx.moveTo(pos.x, pos.y);
      event.preventDefault();
    }

    function move(event) {
      if (!drawing) return;
      const pos = getPos(event);
      ctx.lineWidth = 2;
      ctx.lineCap = "round";
      ctx.strokeStyle = "#1f1f24";
      ctx.lineTo(pos.x, pos.y);
      ctx.stroke();
      output.value = canvas.toDataURL("image/png");
      event.preventDefault();
    }

    function end(event) {
      drawing = false;
      event.preventDefault();
    }

    canvas.addEventListener("mousedown", start);
    canvas.addEventListener("mousemove", move);
    canvas.addEventListener("mouseup", end);
    canvas.addEventListener("mouseleave", end);
    canvas.addEventListener("touchstart", start, { passive: false });
    canvas.addEventListener("touchmove", move, { passive: false });
    canvas.addEventListener("touchend", end);
    clearButton.addEventListener("click", () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      output.value = "";
    });
  }

  setupSignaturePad("customerSignatureCanvas", "customerSignatureData", "clearCustomerSignature");
  setupSignaturePad("executiveSignatureCanvas", "executiveSignatureData", "clearExecutiveSignature");
</script>
{% endblock %}
""",
    "admin/dashboard.html": """{% extends "admin/base.html" %}
{% block title %}Dashboard{% endblock %}
{% block page_heading %}Dashboard{% endblock %}
{% block page_subheading %}Track property inventory, lead momentum, and approval workload in one premium command view.{% endblock %}
{% block page_actions %}
<a href="{{ url_for('admin.properties') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-building me-1"></i>Manage Listings</a>
{% endblock %}
{% block content %}
<section class="kpi-grid">
  <article class="admin-kpi-card">
    <div class="kpi-top">
      <p class="kpi-label">Total Properties</p>
      <span class="kpi-icon"><i class="bi bi-buildings"></i></span>
    </div>
    <h3 class="kpi-value">{{ stats.total_properties }}</h3>
    <p class="kpi-meta">Available: {{ stats.available_properties }} | Sold: {{ stats.sold_properties }}</p>
  </article>

  <article class="admin-kpi-card kpi-highlight">
    <div class="kpi-top">
      <p class="kpi-label">Pending Submissions</p>
      <span class="kpi-icon"><i class="bi bi-hourglass-split"></i></span>
    </div>
    <h3 class="kpi-value">{{ stats.pending_submissions }}</h3>
    <p class="kpi-meta mb-2">Owner approval tasks waiting for review</p>
    <a href="{{ url_for('admin.sell_properties', status='pending') }}" class="btn btn-sm btn-light">Review Now</a>
  </article>

  <article class="admin-kpi-card">
    <div class="kpi-top">
      <p class="kpi-label">Total Leads</p>
      <span class="kpi-icon"><i class="bi bi-people"></i></span>
    </div>
    <h3 class="kpi-value">{{ stats.total }}</h3>
    <p class="kpi-meta">Hot prospects: {{ stats.hot }}</p>
  </article>

  <article class="admin-kpi-card">
    <div class="kpi-top">
      <p class="kpi-label">Visitors</p>
      <span class="kpi-icon"><i class="bi bi-person-walking"></i></span>
    </div>
    <h3 class="kpi-value">{{ stats.total_visitors }}</h3>
    <p class="kpi-meta">Property views: {{ stats.property_views }}</p>
  </article>

  <article class="admin-kpi-card">
    <div class="kpi-top">
      <p class="kpi-label">Conversion</p>
      <span class="kpi-icon"><i class="bi bi-activity"></i></span>
    </div>
    <h3 class="kpi-value">{{ stats.conversion_rate }}%</h3>
    <p class="kpi-meta">Inquiry to qualified lead ratio</p>
  </article>
</section>

<div class="row g-3">
  <div class="col-lg-6">
    <section class="admin-section-card h-100">
      <div class="admin-section-heading">
        <h5>Recent Inquiries</h5>
        <a href="{{ url_for('admin.inquiries') }}" class="btn btn-sm btn-outline-secondary">Open Workflow</a>
      </div>
      <div class="list-group">
      {% for inquiry in recent_inquiries %}
      <a href="{{ url_for('admin.inquiry_detail', inquiry_id=inquiry.id) }}" class="list-group-item list-group-item-action">
        <div class="d-flex justify-content-between align-items-center gap-2">
          <span>{{ inquiry.name }} - {{ inquiry.mobile }}</span>
          <span class="badge bg-secondary">{{ inquiry.status|replace('_', ' ')|title }}</span>
        </div>
      </a>
      {% else %}
      <div class="list-group-item text-muted">No inquiries received yet.</div>
      {% endfor %}
      </div>
    </section>
  </div>

  <div class="col-lg-6">
    <section class="admin-section-card h-100">
      <div class="admin-section-heading">
        <h5>Most Viewed Properties</h5>
      </div>
      <ul class="list-group">
      {% for p in top_properties %}
      <li class="list-group-item d-flex justify-content-between">{{ p.property_name }} <span class="badge bg-secondary">{{ p.view_count }} views</span></li>
      {% else %}
      <li class="list-group-item text-muted">No property views yet.</li>
      {% endfor %}
      </ul>
    </section>
  </div>
</div>
{% endblock %}
""",
    "admin/employees.html": """{% extends "admin/base.html" %}
{% block title %}Employee Permissions{% endblock %}
{% block page_heading %}Employee Permission Management{% endblock %}
{% block page_subheading %}Create employee admins, assign role presets, and control granular access with OTP-secured updates.{% endblock %}
{% block page_actions %}
<span class="badge bg-secondary align-self-center">{{ admins|length }} accounts</span>
{% endblock %}
{% block content %}
{% if setup_payload %}
<section class="admin-section-card mb-3">
  <div class="admin-section-heading">
    <h5>Google Authenticator Setup: {{ setup_payload.username }}</h5>
  </div>
  <div class="row g-3 align-items-center">
    <div class="col-md-4 text-center">
      <img src="{{ setup_payload.qr_url }}" alt="TOTP QR Code" class="img-fluid rounded border" style="max-width: 220px;">
    </div>
    <div class="col-md-8">
      <p class="mb-2"><strong>Secret:</strong> <code>{{ setup_payload.secret }}</code></p>
      <p class="small text-muted mb-2">Scan this QR in Google Authenticator (or compatible app), then verify at next login.</p>
      <div class="small text-muted text-break">{{ setup_payload.otpauth_uri }}</div>
    </div>
  </div>
</section>
{% endif %}

<section class="admin-section-card mb-3">
  <div class="admin-section-heading">
    <h5>Create Employee Admin</h5>
  </div>
  <form method="POST" action="{{ url_for('admin.create_admin_user') }}" class="row g-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="col-md-3">
      <label class="form-label">Username *</label>
      <input class="form-control" name="username" required>
    </div>
    <div class="col-md-3">
      <label class="form-label">Email</label>
      <input type="email" class="form-control" name="email" placeholder="Optional">
    </div>
    <div class="col-md-3">
      <label class="form-label">Full Name</label>
      <input class="form-control" name="full_name">
    </div>
    <div class="col-md-3">
      <label class="form-label">Phone</label>
      <input class="form-control" name="phone" placeholder="+91xxxxxxxxxx">
    </div>
    <div class="col-md-3">
      <label class="form-label">Password *</label>
      <input type="password" class="form-control" name="password" minlength="6" required>
    </div>
    <div class="col-md-3">
      <label class="form-label">Role Preset *</label>
      <select class="form-select" name="role" required>
        {% for opt in role_options %}
        <option value="{{ opt.value }}">{{ opt.title }}</option>
        {% else %}
        {% for role in role_keys %}
        <option value="{{ role }}">{{ role|replace('_', ' ')|title }}</option>
        {% endfor %}
        <option value="broker">Broker</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-12">
      <label class="form-label">Granular Permissions (optional override)</label>      <div class="row row-cols-1 row-cols-md-4 g-2">
        {% for key in permission_keys %}
        <div class="col">
          <label class="form-check border rounded p-2 d-flex align-items-center gap-2">
            <input class="form-check-input mt-0" type="checkbox" name="permissions" value="{{ key }}">
            <span class="small">{{ key }}</span>
          </label>
        </div>
        {% endfor %}
      </div>
      <p class="small text-muted mt-2 mb-0">If no permission is checked, default role preset permissions are applied automatically.</p>
    </div>
    <div class="col-12">
      <button class="btn btn-jk-accent">Create Employee Admin</button>
    </div>
  </form>
</section>

<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Employee Accounts</h5>
  </div>
  <div class="admin-table-wrap table-responsive">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>User</th>
          <th>Role</th>
          <th>Status</th>
          <th>Verification</th>
          <th>Permissions</th>
          <th style="min-width: 290px;">Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for admin_row in admins %}
        <tr>
          <td>
            <div class="fw-semibold">{{ admin_row.full_name or admin_row.username }}</div>
            <div class="small text-muted">{{ admin_row.username }} • {{ admin_row.email }}</div>
            <div class="small text-muted">{{ admin_row.phone or "No phone configured" }}</div>
          </td>
          <td>
            <span class="admin-status-pill status-pending">{{ admin_row.role|replace('_', ' ')|title }}</span>
          </td>
          <td>
            {% if admin_row.is_active %}
            <span class="admin-status-pill status-approved">Active</span>
            {% else %}
            <span class="admin-status-pill status-rejected">Inactive</span>
            {% endif %}
          </td>
          <td class="small">{{ admin_row.verification_summary }}</td>
          <td class="small">{{ admin_row.permission_summary }}</td>
          <td class="text-nowrap">
            <form method="POST" action="{{ url_for('admin.toggle_admin_user', admin_id=admin_row.id) }}" class="d-inline">
              <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
              <input type="hidden" name="is_active" value="{{ 0 if admin_row.is_active else 1 }}">
              <button class="btn btn-sm btn-outline-secondary">{{ "Disable" if admin_row.is_active else "Enable" }}</button>
            </form>
            <a href="{{ url_for('admin.admin_users', edit=admin_row.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
            {% if not admin_row.is_super_admin or admins|selectattr('is_super_admin')|list|length > 1 %}
            <form method="POST" action="{{ url_for('admin.delete_admin_user', admin_id=admin_row.id) }}" class="d-inline" onsubmit="return confirm('Deactivate this account?')">
              <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
              <button class="btn btn-sm btn-outline-danger">Deactivate</button>
            </form>
            {% endif %}
          </td>
        </tr>
        {% if edit_admin_id == admin_row.id %}
        <tr>
          <td colspan="6">
            <div class="border rounded p-3 bg-light-subtle">
              <h6 class="mb-3">Edit: {{ admin_row.username }}</h6>
              <form method="POST" action="{{ url_for('admin.update_admin_user', admin_id=admin_row.id) }}" class="row g-3">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <div class="col-md-3">
                  <label class="form-label">Email</label>
                  <input type="email" class="form-control" name="email" value="{{ admin_row.email }}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Full Name</label>
                  <input class="form-control" name="full_name" value="{{ admin_row.full_name }}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Phone</label>
                  <input class="form-control" name="phone" value="{{ admin_row.phone or '' }}">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Reset Password</label>
                  <input type="password" class="form-control" name="password" minlength="6" placeholder="Leave blank to keep">
                </div>
                <div class="col-md-3">
                  <label class="form-label">Role Preset</label>
                  <select class="form-select" name="role" required>
                    {% for opt in role_options %}
                    <option value="{{ opt.value }}" {% if admin_row.role == opt.value %}selected{% endif %}>{{ opt.title }}</option>
                    {% else %}
                    {% for role in role_keys %}
                    <option value="{{ role }}" {% if admin_row.role == role %}selected{% endif %}>{{ role|replace('_', ' ')|title }}</option>
                    {% endfor %}
                    <option value="broker" {% if admin_row.role == 'broker' %}selected{% endif %}>Broker</option>
                    {% endfor %}
                  </select>
                </div>
                <div class="col-md-9 d-flex align-items-end gap-4">
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="is_active" id="active{{ admin_row.id }}" value="1" {% if admin_row.is_active %}checked{% endif %}>
                    <label class="form-check-label" for="active{{ admin_row.id }}">Active</label>
                  </div>
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="require_otp" id="req{{ admin_row.id }}" value="1" {% if admin_row.require_otp %}checked{% endif %}>
                    <label class="form-check-label" for="req{{ admin_row.id }}">Require OTP</label>
                  </div>
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="mobile_otp_enabled" id="mob{{ admin_row.id }}" value="1" {% if admin_row.mobile_otp_enabled %}checked{% endif %}>
                    <label class="form-check-label" for="mob{{ admin_row.id }}">Enable Mobile OTP</label>
                  </div>
                  <div class="form-check">
                    <input class="form-check-input" type="checkbox" name="phone_verified" id="pv{{ admin_row.id }}" value="1" {% if admin_row.phone_verified %}checked{% endif %}>
                    <label class="form-check-label" for="pv{{ admin_row.id }}">Phone Verified</label>
                  </div>
                </div>
                <div class="col-12">
                  <label class="form-label">Permission Matrix</label>
                  <div class="row row-cols-1 row-cols-md-4 g-2">
                    {% for key in permission_keys %}
                    <div class="col">
                      <label class="form-check border rounded p-2 d-flex align-items-center gap-2">
                        <input class="form-check-input mt-0" type="checkbox" name="permissions" value="{{ key }}" {% if admin_row.has_permission(key) %}checked{% endif %}>
                        <span class="small">{{ key }}</span>
                      </label>
                    </div>
                    {% endfor %}
                  </div>
                </div>
                <div class="col-12 d-flex gap-2">
                  <button class="btn btn-jk-accent">Save Employee Access</button>
                  <a class="btn btn-outline-secondary" href="{{ url_for('admin.admin_users') }}">Cancel</a>
                </div>
              </form>
              <hr class="my-3">
              <div class="d-flex flex-wrap align-items-center gap-2">
                <form method="POST" action="{{ url_for('admin.setup_admin_totp', admin_id=admin_row.id) }}">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <button class="btn btn-sm btn-outline-dark">Setup TOTP</button>
                </form>
                <form method="POST" action="{{ url_for('admin.setup_admin_totp', admin_id=admin_row.id) }}">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <input type="hidden" name="regenerate" value="1">
                  <button class="btn btn-sm btn-outline-secondary">Regenerate TOTP Secret</button>
                </form>
                <form method="POST" action="{{ url_for('admin.disable_admin_totp', admin_id=admin_row.id) }}" onsubmit="return confirm('Disable Google Authenticator for this account?')">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <button class="btn btn-sm btn-outline-danger">Disable TOTP</button>
                </form>
                {% if setup_payload and setup_payload.admin_id == admin_row.id %}
                <a class="btn btn-sm btn-outline-primary" href="#totp-setup-anchor">View Latest Setup QR</a>
                {% endif %}
              </div>
            </div>
          </td>
        </tr>
        {% endif %}
        {% else %}
        <tr>
          <td colspan="6" class="text-center text-muted py-4">No employee admin accounts found.</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>

<section class="admin-section-card mt-3">
  <div class="admin-section-heading">
    <h5>Default Role Permission Presets</h5>
  </div>
  <div class="row g-3">
    {% for opt in role_options %}
    <div class="col-md-6 col-lg-3">
      <div class="border rounded p-3 h-100">
        <h6 class="mb-2">{{ opt.title }}</h6>
        <ul class="small mb-0">
          {% for key in opt.permissions %}
          <li>{{ key }}</li>
          {% else %}
          <li>No default permissions</li>
          {% endfor %}
        </ul>
      </div>
    </div>
    {% else %}
    {% for role in role_keys %}
    <div class="col-md-6 col-lg-3">
      <div class="border rounded p-3 h-100">
        <h6 class="mb-2">{{ role|replace('_', ' ')|title }}</h6>
        <ul class="small mb-0">
          {% for key in role_presets.get(role, []) %}
          <li>{{ key }}</li>
          {% else %}
          <li>No default permissions</li>
          {% endfor %}
        </ul>
      </div>
    </div>
    {% endfor %}
    <div class="col-md-6 col-lg-3">
      <div class="border rounded p-3 h-100">
        <h6 class="mb-2">Broker</h6>
        <ul class="small mb-0">
          <li>manage_properties</li>
          <li>manage_leads</li>
          <li>manage_inquiries</li>
        </ul>
      </div>
    </div>
    {% endfor %}
  </div>
</section>
{% if setup_payload %}
<div id="totp-setup-anchor"></div>
{% endif %}
{% endblock %}
""",
    "admin/forgot_password_identify.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Forgot Password - {{ company_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/admin.css') }}" rel="stylesheet">
</head>
<body class="admin-login-page">
  <div class="admin-login-shell">
    <section class="admin-login-intro">
      <span class="admin-login-chip">Account Recovery</span>
      <h1>{{ company_name }}</h1>
      <p>Reset access for admin and employee accounts using identity details and OTP verification.</p>
      <ul class="admin-login-feature-list">
        <li><i class="bi bi-person-badge"></i> Identify with username or email</li>
        <li><i class="bi bi-phone"></i> Add registered mobile when mobile OTP is enabled</li>
        <li><i class="bi bi-shield-lock"></i> Continue only after OTP verification</li>
      </ul>
    </section>

    <section class="admin-login-card">
      <div class="text-center mb-4">
        <span class="admin-login-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" class="jk-logo jk-logo-mark" alt="{{ company_name }}">
        </span>
        <h4 class="mt-3 mb-1">Forgot Password</h4>
        <p class="text-muted mb-0">Step 1 of 3: Verify account details</p>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
      {% endfor %}
      {% endwith %}

      <form method="POST" class="admin-login-form">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <div class="mb-3">
          <label for="identifier">Username or Email</label>
          <input
            id="identifier"
            class="form-control"
            name="identifier"
            value="{{ identifier or '' }}"
            autocomplete="username"
            required
          >
        </div>
        <div class="mb-3">
          <label for="mobile">Registered Mobile (required for mobile OTP accounts)</label>
          <input
            id="mobile"
            class="form-control"
            name="mobile"
            value="{{ mobile or '' }}"
            autocomplete="tel"
            placeholder="e.g. +91XXXXXXXXXX"
          >
        </div>
        <button class="btn btn-jk-accent w-100">Continue to OTP</button>
      </form>
      <div class="text-center mt-3">
        <a href="{{ url_for('auth.admin_login') }}" class="small">Back to admin login</a>
      </div>
    </section>
  </div>
</body>
</html>
""",
    "admin/forgot_password_reset.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Set New Password - {{ company_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/admin.css') }}" rel="stylesheet">
</head>
<body class="admin-login-page">
  <div class="admin-login-shell">
    <section class="admin-login-intro">
      <span class="admin-login-chip">New Password</span>
      <h1>{{ company_name }}</h1>
      <p>Step 3 of 3 for <strong>{{ reset_admin.username }}</strong>. Set a fresh password to recover admin access.</p>
      <ul class="admin-login-feature-list">
        <li><i class="bi bi-lock"></i> Minimum 8 characters</li>
        <li><i class="bi bi-type"></i> Include at least one letter</li>
        <li><i class="bi bi-123"></i> Include at least one number</li>
      </ul>
    </section>

    <section class="admin-login-card">
      <div class="text-center mb-4">
        <span class="admin-login-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" class="jk-logo jk-logo-mark" alt="{{ company_name }}">
        </span>
        <h4 class="mt-3 mb-1">Set New Password</h4>
        <p class="text-muted mb-0">Step 3 of 3</p>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
      {% endfor %}
      {% endwith %}

      <form method="POST" class="admin-login-form">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <div class="mb-3">
          <label for="password">New Password</label>
          <input id="password" type="password" class="form-control" name="password" autocomplete="new-password" required>
        </div>
        <div class="mb-3">
          <label for="confirm_password">Confirm New Password</label>
          <input id="confirm_password" type="password" class="form-control" name="confirm_password" autocomplete="new-password" required>
        </div>
        <button class="btn btn-jk-accent w-100">Update Password</button>
      </form>
      <div class="text-center mt-3">
        <a href="{{ url_for('auth.admin_login') }}" class="small">Back to admin login</a>
      </div>
    </section>
  </div>
</body>
</html>
""",
    "admin/forgot_password_verify.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Verify Reset OTP - {{ company_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/admin.css') }}" rel="stylesheet">
</head>
<body class="admin-login-page">
  <div class="admin-login-shell">
    <section class="admin-login-intro">
      <span class="admin-login-chip">Identity Verification</span>
      <h1>{{ company_name }}</h1>
      <p>Step 2 of 3 for <strong>{{ pending_admin.username }}</strong>. Submit OTP to continue password reset.</p>
      <ul class="admin-login-feature-list">
        <li><i class="bi bi-clock-history"></i> OTP validity and cooldown enforced</li>
        <li><i class="bi bi-shield-check"></i> Brute-force protection on failed attempts</li>
        <li><i class="bi bi-key"></i> Password reset unlocks only after successful OTP</li>
      </ul>
    </section>

    <section class="admin-login-card">
      <div class="text-center mb-4">
        <span class="admin-login-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" class="jk-logo jk-logo-mark" alt="{{ company_name }}">
        </span>
        <h4 class="mt-3 mb-1">Verify OTP</h4>
        <p class="text-muted mb-0">Step 2 of 3</p>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
      {% endfor %}
      {% endwith %}

      {% if phone_hint %}
      <div class="alert alert-secondary small">
        Registered mobile ending with <strong>{{ phone_hint[-4:] }}</strong> can receive OTP.
      </div>
      {% endif %}

      {% if dev_otp %}
      <div class="alert alert-warning small">
        <strong>Development fallback active:</strong> OTP code is <code>{{ dev_otp }}</code>.
      </div>
      {% endif %}

      {% if show_mobile %}
      <form method="POST" class="admin-login-form mb-2">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="action" value="verify_mobile">
        <label for="mobile_otp">Mobile OTP Code</label>
        <input id="mobile_otp" class="form-control mb-2" name="mobile_otp" autocomplete="one-time-code" placeholder="OTP from SMS" required>
        <button class="btn btn-jk-accent w-100">Verify Mobile OTP</button>
      </form>
      <form method="POST" class="mb-3">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="action" value="resend_mobile">
        <button class="btn btn-link p-0">Resend mobile OTP</button>
      </form>
      {% endif %}

      {% if show_totp %}
      <form method="POST" class="admin-login-form mb-3">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="action" value="verify_totp">
        <label for="totp_code">Authenticator Code</label>
        <input id="totp_code" class="form-control mb-2" name="totp_code" autocomplete="one-time-code" placeholder="6-digit code" required>
        <button class="btn btn-outline-dark w-100">Verify Authenticator Code</button>
      </form>
      {% endif %}

      <div class="text-center">
        <a href="{{ url_for('auth.admin_forgot_password') }}" class="small">Start again</a>
      </div>
    </section>
  </div>
</body>
</html>
""",
    "admin/inquiries.html": """{% extends "admin/base.html" %}
{% block title %}Inquiries{% endblock %}
{% block page_heading %}Inquiries{% endblock %}
{% block page_subheading %}Operational inquiry workflow with category filters, inline updates, and print-ready output.{% endblock %}
{% block page_actions %}
<a
  class="btn btn-outline-secondary btn-sm"
  target="_blank"
  href="{{ url_for('admin.print_inquiries', range=range_filter, start_date=start_date, end_date=end_date, status=selected_status if selected_status != 'all' else '', inquiry_type=selected_inquiry_type if selected_inquiry_type != 'all' else '') }}"
>
  <i class="bi bi-printer me-1"></i>Print View
</a>
{% endblock %}
{% block content %}
<section class="admin-section-card">
  <form method="GET" class="row g-3 align-items-end" id="inquiryFilterForm">
    <div class="col-md-3">
      <label class="form-label">Range</label>
      <select name="range" class="form-select">
        <option value="day" {% if range_filter == 'day' %}selected{% endif %}>Day</option>
        <option value="week" {% if range_filter == 'week' %}selected{% endif %}>Week</option>
        <option value="custom" {% if range_filter == 'custom' %}selected{% endif %}>Custom</option>
      </select>
    </div>
    <div class="col-md-3">
      <label class="form-label">Start Date</label>
      <input type="date" name="start_date" class="form-control" value="{{ start_date }}">
    </div>
    <div class="col-md-3">
      <label class="form-label">End Date</label>
      <input type="date" name="end_date" class="form-control" value="{{ end_date }}">
    </div>
    <div class="col-md-3">
      <label class="form-label">Status</label>
      <select name="status" class="form-select">
        <option value="" {% if selected_status == 'all' %}selected{% endif %}>All</option>
        {% for status in statuses %}
        <option value="{{ status }}" {% if selected_status == status %}selected{% endif %}>{{ status|replace('_', ' ')|title }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-12">
      <input type="hidden" name="inquiry_type" id="inquiryTypeInput" value="{{ selected_inquiry_type }}">
      <div class="admin-filter-bar d-flex flex-wrap gap-2 mb-2">
        {% for value, label in inquiry_types %}
        <button type="button" class="admin-filter-chip {% if selected_inquiry_type == value %}active{% endif %}" data-inquiry-type="{{ value }}">{{ label }}</button>
        {% endfor %}
      </div>
    </div>
    <div class="col-12 d-flex gap-2">
      <button class="btn btn-jk-accent">Apply Filters</button>
      <a class="btn btn-outline-secondary" href="{{ url_for('admin.inquiries') }}">Reset</a>
    </div>
  </form>
</section>

<div class="d-flex justify-content-between align-items-center mb-2">
  <div class="small text-muted">Select rows to bulk-delete the current filtered set.</div>
  <button type="button" class="btn btn-sm btn-outline-danger" id="bulkDeleteInquiriesBtn">Delete Selected</button>
</div>
<div class="admin-table-wrap table-responsive">
  <table class="table align-middle">
    <thead>
      <tr>
        <th style="width:36px;"><input type="checkbox" id="selectAllInquiries"></th>
        <th>Date</th>
        <th>Category</th>
        <th>Name</th>
        <th>Mobile</th>
        <th>Property</th>
        <th>Message</th>
        <th>Status / Notes</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for i in inquiries %}
      {% set itype = i.inquiry_type or ('property' if i.property_id else 'general') %}
      <tr>
        <td><input type="checkbox" value="{{ i.id }}" class="inquiry-check"></td>
        <td>{{ i.created_at }}</td>
        <td>
          <span class="badge text-bg-secondary">
            {% if itype == 'site_visit' %}Site Visit{% elif itype == 'property' %}Property{% else %}General{% endif %}
          </span>
        </td>
        <td class="fw-semibold">{{ i.name }}</td>
        <td>{{ i.mobile }}</td>
        <td>{{ i.property_name or 'General' }}</td>
        <td>{{ i.message or '—' }}</td>
        <td style="min-width: 280px;">
          <form method="POST" action="{{ url_for('admin.update_inquiry', inquiry_id=i.id) }}" class="d-grid gap-2">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <select class="form-select form-select-sm" name="status">
              {% for status in statuses %}
              <option value="{{ status }}" {% if i.status == status %}selected{% endif %}>{{ status|replace('_', ' ')|title }}</option>
              {% endfor %}
            </select>
            <textarea class="form-control form-control-sm" rows="2" name="notes" placeholder="Add notes">{{ i.notes or '' }}</textarea>
            <button class="btn btn-sm btn-outline-primary">Save</button>
          </form>
        </td>
        <td class="text-nowrap">
          <a href="{{ url_for('admin.inquiry_detail', inquiry_id=i.id) }}" class="btn btn-sm btn-outline-secondary">Detail</a>
          <form method="POST" action="{{ url_for('admin.delete_inquiry', inquiry_id=i.id) }}" class="d-inline" onsubmit="return confirm('Delete this inquiry?');">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <button class="btn btn-sm btn-outline-danger">Delete</button>
          </form>
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="9" class="text-center text-muted py-4">No inquiries for the selected filter.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
<form method="POST" action="{{ url_for('admin.bulk_delete_inquiries') }}" id="bulkInquiryForm" class="d-none">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
</form>
{% endblock %}
{% block extra_js %}
<script>
  document.querySelectorAll('[data-inquiry-type]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.getElementById('inquiryTypeInput').value = btn.dataset.inquiryType || 'all';
      document.getElementById('inquiryFilterForm').submit();
    });
  });
  document.getElementById('selectAllInquiries')?.addEventListener('change', (e) => {
    document.querySelectorAll('.inquiry-check').forEach((cb) => { cb.checked = e.target.checked; });
  });
  document.getElementById('bulkDeleteInquiriesBtn')?.addEventListener('click', () => {
    const form = document.getElementById('bulkInquiryForm');
    form.querySelectorAll('input[name="inquiry_ids"]').forEach((n) => n.remove());
    const checked = [...document.querySelectorAll('.inquiry-check:checked')];
    if (!checked.length) { alert('Select at least one inquiry.'); return; }
    if (!confirm('Delete selected inquiries?')) return;
    checked.forEach((cb) => {
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'inquiry_ids';
      input.value = cb.value;
      form.appendChild(input);
    });
    form.submit();
  });
</script>
{% endblock %}
""",
    "admin/inquiries_print.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Inquiries Print</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    @media print {
      .no-print { display: none !important; }
      body { margin: 0; }
    }
    .cat-badge { font-size: 0.75rem; }
  </style>
</head>
<body class="p-3">
  <div class="d-flex justify-content-between align-items-center mb-3 no-print">
    <h4 class="mb-0">Inquiries Report</h4>
    <button class="btn btn-dark btn-sm" onclick="window.print()">Print</button>
  </div>
  <div class="mb-2 small text-muted">
    Range: {{ range_filter|title }} | Dates: {{ start_date }} to {{ end_date }} | Status: {{ selected_status|replace('_', ' ')|title }}
    | Category:
    {% if selected_inquiry_type == 'site_visit' %}Site Visit Requests
    {% elif selected_inquiry_type == 'property' %}Property-Specific Inquiries
    {% elif selected_inquiry_type == 'general' %}General Inquiries
    {% else %}All{% endif %}
  </div>
  <table class="table table-sm table-bordered align-middle">
    <thead class="table-light">
      <tr>
        <th>Date</th>
        <th>Category</th>
        <th>Name</th>
        <th>Mobile</th>
        <th>Email</th>
        <th>Property</th>
        <th>Status</th>
        <th>Notes</th>
      </tr>
    </thead>
    <tbody>
      {% for inquiry in inquiries %}
      {% set itype = inquiry.inquiry_type or ('property' if inquiry.property_id else 'general') %}
      <tr>
        <td>{{ inquiry.created_at }}</td>
        <td>
          <span class="badge text-bg-secondary cat-badge">
            {% if itype == 'site_visit' %}Site Visit{% elif itype == 'property' %}Property{% else %}General{% endif %}
          </span>
        </td>
        <td>{{ inquiry.name }}</td>
        <td>{{ inquiry.mobile }}</td>
        <td>{{ inquiry.email or '-' }}</td>
        <td>{{ inquiry.property_name or 'General' }}</td>
        <td>{{ inquiry.status|replace('_', ' ')|title }}</td>
        <td>{{ inquiry.notes or '-' }}</td>
      </tr>
      {% else %}
      <tr>
        <td colspan="8" class="text-center">No inquiries available.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
""",
    "admin/inquiry_detail.html": """{% extends "admin/base.html" %}
{% block title %}Inquiry Detail{% endblock %}
{% block page_heading %}Inquiry Detail{% endblock %}
{% block page_subheading %}Sensitive contact detail view with quick status and note updates.{% endblock %}
{% block page_actions %}
<a href="{{ url_for('admin.inquiries') }}" class="btn btn-outline-secondary btn-sm">
  <i class="bi bi-arrow-left me-1"></i>Back to Inquiries
</a>
{% endblock %}
{% block content %}
<section class="admin-section-card">
  <div class="row g-3 mb-3">
    <div class="col-md-6">
      <label>Name</label>
      <div class="form-control bg-light">{{ inquiry.name }}</div>
    </div>
    <div class="col-md-3">
      <label>Mobile</label>
      <div class="form-control bg-light">{{ inquiry.mobile }}</div>
    </div>
    <div class="col-md-3">
      <label>Email</label>
      <div class="form-control bg-light">{{ inquiry.email or '-' }}</div>
    </div>
    <div class="col-md-6">
      <label>Property</label>
      <div class="form-control bg-light">{{ inquiry.property_name or 'General Inquiry' }}</div>
    </div>
    <div class="col-md-6">
      <label>Source</label>
      <div class="form-control bg-light">{{ inquiry.source or '-' }}</div>
    </div>
    <div class="col-12">
      <label>Message</label>
      <div class="form-control bg-light" style="min-height: 86px;">{{ inquiry.message or '-' }}</div>
    </div>
  </div>

  <form method="POST" action="{{ url_for('admin.update_inquiry', inquiry_id=inquiry.id) }}" class="row g-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="col-md-3">
      <label>Status</label>
      <select class="form-select" name="status">
        {% for status in statuses %}
        <option value="{{ status }}" {% if inquiry.status == status %}selected{% endif %}>{{ status|replace('_', ' ')|title }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-9">
      <label>Notes</label>
      <textarea class="form-control" name="notes" rows="3" placeholder="Internal notes">{{ inquiry.notes or '' }}</textarea>
    </div>
    <div class="col-12">
      <button class="btn btn-jk-accent">Save Inquiry Update</button>
    </div>
  </form>
</section>
{% endblock %}
""",
    "admin/lead_detail.html": """{% extends "admin/base.html" %}
{% block title %}Lead {{ lead.name }}{% endblock %}
{% block page_heading %}Lead: {{ lead.name }}{% endblock %}
{% block page_subheading %}Update lead status, schedule follow-ups, and keep a clean communication timeline.{% endblock %}
{% block page_actions %}
<a href="{{ url_for('admin.leads') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left me-1"></i>Back to Leads</a>
<a href="{{ url_for('admin.lead_export_pdf', lid=lead.id) }}" class="btn btn-outline-danger btn-sm"><i class="bi bi-file-earmark-pdf me-1"></i>Export Lead PDF</a>
{% endblock %}
{% block content %}
<div class="row g-4">
  <div class="col-md-6">
    <div class="admin-section-card h-100">
      <p><strong>Mobile:</strong> <a href="tel:{{ lead.mobile }}">{{ lead.mobile }}</a></p>
      {% if current_user.role != 'caller' %}
      <p><strong>Email:</strong> {{ lead.email or '—' }}</p>
      <p><strong>Budget:</strong> {% if lead.budget %}₹{{ "{:,.0f}".format(lead.budget) }}{% else %}—{% endif %}</p>
      <p><strong>Preferred Area:</strong> {{ lead.preferred_area or '—' }}</p>
      <p><strong>Property:</strong> {{ lead.property_name or '—' }}</p>
      <p><strong>Score:</strong> {{ lead.lead_score }} ({{ lead.lead_tier }})</p>
      <p><strong>Inquiry:</strong> {{ lead.inquiry_date }}</p>
      {% else %}
      <p class="text-muted small mb-0">Caller role has phone-first access with limited follow-up actions.</p>
      {% endif %}
    </div>
  </div>
  <div class="col-md-6">
    <form method="POST" action="{{ url_for('admin.update_lead', lid=lead.id) }}" class="admin-section-card h-100">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <label>Status</label>
      <select class="form-select mb-2" name="status">
        {% for s in statuses %}<option value="{{ s }}" {% if lead.status==s %}selected{% endif %}>{{ s }}</option>{% endfor %}
      </select>
      <label>Follow-up Date</label>
      <input type="date" class="form-control mb-2" name="follow_up_date">
      <label>Note</label>
      <textarea class="form-control mb-2" name="note" rows="3"></textarea>
      <button class="btn btn-jk-accent">Update Lead</button>
    </form>
  </div>
</div>
<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Notes</h5>
  </div>
  <ul class="list-group">
    {% for n in notes %}
    <li class="list-group-item">{{ n.note }} <small class="text-muted">— {{ n.created_at }}</small></li>
    {% else %}
    <li class="list-group-item text-muted">No notes yet.</li>
    {% endfor %}
  </ul>
</section>
{% endblock %}
""",
    "admin/leads.html": """{% extends "admin/base.html" %}
{% block title %}Leads{% endblock %}
{% block page_heading %}Lead Management{% endblock %}
{% block page_subheading %}Prioritize high-intent prospects, monitor status flow, and jump directly into follow-up actions.{% endblock %}
{% block page_actions %}
<a href="{{ url_for('admin.leads_export_pdf') }}{% if request.query_string %}?{{ request.query_string.decode('utf-8') }}{% endif %}" class="btn btn-outline-danger btn-sm">
  <i class="bi bi-file-earmark-pdf me-1"></i>Download PDF Report
</a>
{% endblock %}
{% block content %}
<div class="admin-filter-bar mb-2 d-flex flex-wrap align-items-center gap-2">
  <a href="?" class="admin-filter-chip {% if not request.args.get('status') and not request.args.get('tier') %}active{% endif %}">All</a>
  {% for s in statuses %}
  <a href="?status={{ s }}" class="admin-filter-chip {% if request.args.get('status') == s %}active{% endif %}">{{ s|title }}</a>
  {% endfor %}
  <a href="?tier=hot" class="admin-filter-chip {% if request.args.get('tier') == 'hot' %}active{% endif %}">Hot</a>
  <a href="{{ url_for('admin.leads_export_pdf') }}{% if request.query_string %}?{{ request.query_string.decode('utf-8') }}{% endif %}" class="btn btn-outline-danger btn-sm ms-auto">
    <i class="bi bi-file-earmark-pdf me-1"></i>Download PDF Report
  </a>
</div>

<div class="admin-table-wrap table-responsive">
  <table class="table align-middle">
    <thead>
      <tr>
        <th>Name</th>
        <th>Mobile</th>
        {% if current_user.role != 'caller' %}
        <th>Area</th>
        <th>Score</th>
        <th>Tier</th>
        {% endif %}
        <th>Status</th>
        <th>Action</th>
      </tr>
    </thead>
    <tbody>
      {% for l in leads %}
      <tr class="lead-{{ l.lead_tier }}">
        <td class="fw-semibold">{{ l.name }}{% if l.is_urgent %} <span class="badge bg-warning text-dark">Urgent</span>{% endif %}</td>
        <td>{{ l.mobile }}</td>
        {% if current_user.role != 'caller' %}
        <td>{{ l.preferred_area or '—' }}</td>
        <td>{{ l.lead_score }}</td>
        <td><span class="admin-status-pill status-{{ l.lead_tier }}">{{ l.lead_tier }}</span></td>
        {% endif %}
        <td>{{ l.status }}</td>
        <td><a href="{{ url_for('admin.lead_detail', lid=l.id) }}" class="btn btn-sm btn-outline-primary">View</a></td>
      </tr>
      {% else %}
      <tr>
        <td colspan="{{ 7 if current_user.role != 'caller' else 4 }}" class="text-center text-muted py-4">No leads found for this filter.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""",
    "admin/login.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Login - {{ company_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/admin.css') }}" rel="stylesheet">
</head>
<body class="admin-login-page">
  <div class="admin-login-shell">
    <section class="admin-login-intro">
      <span class="admin-login-chip">Secure Access</span>
      <h1>{{ company_name }}</h1>
      <p>Premium control room for properties, leads, submissions, and performance analytics.</p>
      <ul class="admin-login-feature-list">
        <li><i class="bi bi-grid-1x2"></i> Modern command-center dashboard</li>
        <li><i class="bi bi-shield-lock"></i> Protected workflows and approvals</li>
        <li><i class="bi bi-graph-up-arrow"></i> Live business visibility</li>
      </ul>
    </section>

    <section class="admin-login-card">
      <div class="text-center mb-4">
        <span class="admin-login-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" class="jk-logo jk-logo-mark" alt="{{ company_name }}">
        </span>
        <h4 class="mt-3 mb-1">Admin Portal</h4>
        <p class="text-muted mb-0">Sign in to continue</p>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
      {% endfor %}
      {% endwith %}

      <form method="POST" class="admin-login-form">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="next" value="{{ request.args.get('next', '') }}">
        <div class="mb-3">
          <label for="username">Username</label>
          <input id="username" class="form-control" name="username" autocomplete="username" required>
        </div>
        <div class="mb-3">
          <label for="password">Password</label>
          <input id="password" type="password" class="form-control" name="password" autocomplete="current-password" required>
        </div>
        <button class="btn btn-jk-accent w-100">Login</button>
      </form>
      <p class="small text-muted mt-3 mb-0 text-center">Credentials are managed by your administrator.</p>
    </section>
  </div>
</body>
</html>
""",
    "admin/price_predictor.html": """{% extends "admin/base.html" %}
{% block title %}Price Predictor{% endblock %}
{% block page_heading %}AI Price Predictor{% endblock %}
{% block page_subheading %}Estimate property market value quickly with cleaner input controls and result presentation.{% endblock %}
{% block content %}
<section class="admin-section-card col-xl-6 col-lg-8">
  <form method="POST">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="mb-2"><label>Area</label><input class="form-control" name="area_name" value="{{ request.form.area_name or 'Vesu' }}" required></div>
    <div class="mb-2"><label>BHK</label><input type="number" class="form-control" name="bhk" value="{{ request.form.bhk or 2 }}"></div>
    <div class="mb-2"><label>Sq Ft</label><input type="number" class="form-control" name="sq_ft" value="{{ request.form.sq_ft or 1200 }}" required></div>
    <div class="mb-2"><label>Type</label>
      <select class="form-select" name="property_type">{% for t in types %}<option value="{{ t }}">{{ t }}</option>{% endfor %}</select>
    </div>
    <button class="btn btn-jk-accent">Predict Value</button>
  </form>
</section>
{% if result %}
<div class="alert alert-success mt-2 col-xl-6 col-lg-8">
  <h5>Estimated Market Value: ₹{{ "{:,.0f}".format(result.estimated_value) }}</h5>
  <p>Range: ₹{{ "{:,.0f}".format(result.price_range_low) }} — ₹{{ "{:,.0f}".format(result.price_range_high) }}</p>
  <p>Per sq.ft: ₹{{ "{:,.0f}".format(result.per_sqft) }} ({{ result.method }})</p>
</div>
{% endif %}
{% endblock %}
""",
    "admin/properties.html": """{% extends "admin/base.html" %}
{% block title %}Properties{% endblock %}
{% block page_heading %}Property Inventory{% endblock %}
{% block page_subheading %}Manage listings, monitor inventory status, and jump into edits or submission reviews quickly.{% endblock %}
{% block page_actions %}
<a href="{{ url_for('admin.property_form') }}" class="btn btn-jk-accent btn-sm"><i class="bi bi-plus-circle me-1"></i>Add Property</a>
{% endblock %}
{% block content %}
<div class="admin-filter-bar mb-2" role="group" aria-label="Property status filter">
  <a href="{{ url_for('admin.properties') }}" class="admin-filter-chip {% if selected_status == 'all' %}active{% endif %}">All</a>
  {% for status in statuses %}
  <a href="{{ url_for('admin.properties', status=status) }}" class="admin-filter-chip {% if selected_status == status %}active{% endif %}">{{ status|replace('_', ' ')|title }}</a>
  {% endfor %}
</div>
<div class="admin-table-wrap table-responsive">
  <table class="table align-middle">
    <thead>
      <tr>
        <th>ID</th>
        <th>Name</th>
        <th>Area</th>
        <th>Type</th>
        <th>Price</th>
        <th>Source</th>
        <th>Status</th>
        <th>Views</th>
        <th>Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for p in properties %}
      {% set status_label = 'pending approval' if p.status == 'reserved' else p.status %}
      <tr>
        <td>{{ p.id }}</td>
        <td class="fw-semibold">{{ p.property_name }}</td>
        <td>{{ p.area_name }}</td>
        <td>{{ p.property_type }}</td>
        <td>₹{{ "{:,.0f}".format(p.price) }}</td>
        <td>
          <span class="admin-status-pill status-{{ 'available' if p.creation_source == 'admin' else 'pending' }}">
            {{ 'Admin' if p.creation_source == 'admin' else 'User Submission' }}
          </span>
        </td>
        <td><span class="admin-status-pill status-{{ p.status }}">{{ status_label|title }}</span></td>
        <td>{{ p.view_count }}</td>
        <td class="text-nowrap">
          <a href="{{ url_for('admin.property_form', pid=p.id) }}" class="btn btn-sm btn-outline-primary">Edit</a>
          {% if p.status == 'reserved' and submission_map.get(p.id) %}
          <a href="{{ url_for('admin.sell_properties', status='pending') }}#submission-{{ submission_map.get(p.id).id }}" class="btn btn-sm btn-outline-secondary">Review</a>
          {% endif %}
          <button type="button" class="btn btn-sm btn-outline-danger" data-bs-toggle="modal" data-bs-target="#deletePropertyModal{{ p.id }}">
            Delete
          </button>
          <div class="modal fade" id="deletePropertyModal{{ p.id }}" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog">
              <div class="modal-content">
                <form method="POST" action="{{ url_for('admin.delete_property', pid=p.id) }}">
                  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                  <input type="hidden" name="confirm_property_id" value="{{ p.id }}">
                  <div class="modal-header">
                    <h5 class="modal-title">Confirm Property Deletion</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                  </div>
                  <div class="modal-body">
                    <p class="mb-2">This action permanently deletes <strong>{{ p.property_name }}</strong>.</p>
                    <p class="small text-muted">Type <strong>DELETE</strong> to confirm.</p>
                    <input
                      class="form-control"
                      name="confirm_text"
                      placeholder="Type DELETE"
                      autocomplete="off"
                      required
                      pattern="DELETE"
                    >
                  </div>
                  <div class="modal-footer">
                    <button type="button" class="btn btn-outline-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button class="btn btn-outline-danger">Delete Property</button>
                  </div>
                </form>
              </div>
            </div>
          </div>
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="9" class="text-center text-muted py-4">No properties found for this filter.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""",
    "admin/property_form.html": """{% extends "admin/base.html" %}
{% block title %}{{ 'Edit' if property else 'Add' }} Property{% endblock %}
{% block page_heading %}{{ 'Edit' if property else 'Add' }} Property{% endblock %}
{% block page_subheading %}Capture complete listing information with polished form controls and better visual grouping.{% endblock %}
{% block page_actions %}
<a href="{{ url_for('admin.properties') }}" class="btn btn-outline-secondary btn-sm"><i class="bi bi-arrow-left me-1"></i>Back to Properties</a>
{% endblock %}
{% block content %}
<form method="POST" enctype="multipart/form-data" class="admin-section-card" id="adminPropertyForm">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
  <div class="row g-3">
    <div class="col-md-8"><label>Property Name *</label><input class="form-control" name="property_name" value="{{ property.property_name if property else '' }}" required></div>
    <div class="col-md-4"><label>Type *</label>
      <select class="form-select" name="property_type" id="adminPropertyType" required>
        {% for t in types %}<option value="{{ t }}" {% if property and property.property_type==t %}selected{% endif %}>{{ t }}</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-4"><label>Area *</label><input class="form-control" name="area_name" list="areas" value="{{ property.area_name if property else '' }}" required>
      <datalist id="areas">{% for a in areas %}<option value="{{ a }}">{% endfor %}</datalist>
    </div>
    <div class="col-md-4"><label>Price ₹ *</label><input type="number" class="form-control" name="price" value="{{ property.price if property else '' }}" required></div>
    <div class="col-md-4"><label>Status</label>
      <select class="form-select" name="status">
        {% for s in ['available','reserved','sold','rented'] %}
        <option value="{{ s }}" {% if property and property.status==s %}selected{% endif %}>
          {% if s == 'reserved' %}pending_approval{% else %}{{ s }}{% endif %}
        </option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3" id="adminBhkWrap"><label>BHK Number</label><input type="number" class="form-control" name="bhk" id="adminBhkInput" value="{{ property.bhk if property else 0 }}"></div>
    <div class="col-md-3"><label>Block / Wing</label><input class="form-control" name="block_wing" value="{{ property.block_wing if property and property.block_wing else '' }}" placeholder="A, B, C"></div>
    <div class="col-md-3"><label>Unit Number</label><input class="form-control" name="unit_number" value="{{ property.unit_number if property and property.unit_number else '' }}" placeholder="101, 903"></div>
    <div class="col-md-3"><label>Sq Ft *</label><input type="number" class="form-control" name="sq_ft" value="{{ property.sq_ft if property else '' }}" required></div>
    <div class="col-md-3"><label>Latitude</label><input class="form-control" name="latitude" value="{{ property.latitude if property else '21.1702' }}"></div>
    <div class="col-md-3"><label>Longitude</label><input class="form-control" name="longitude" value="{{ property.longitude if property else '72.8311' }}"></div>
    <div class="col-12"><label>Address</label><input class="form-control" name="address" value="{{ property.address if property else '' }}"></div>
    <div class="col-12"><label>Description</label><textarea class="form-control" name="description" rows="4">{{ property.description if property else '' }}</textarea></div>
    <div class="col-12"><label>Amenities (comma-separated)</label>
      <input class="form-control" name="amenities" value="{% if property and property.amenities %}{{ property.amenities|join(', ') }}{% endif %}">
    </div>
    <div class="col-md-4"><label>Sell vs Rent *</label>
      <select class="form-select" name="listing_intent">
        {% set intent = (property.listing_intent if property else 'sell') %}
        {% if intent not in ['sell','rent'] %}
          {% set intent = 'rent' if property and property.listing_type == 'rent' else 'sell' %}
        {% endif %}
        <option value="sell" {% if intent == 'sell' %}selected{% endif %}>Sell Property</option>
        <option value="rent" {% if intent == 'rent' %}selected{% endif %}>Rent Property</option>
      </select>
      <input type="hidden" name="listing_type" id="adminListingType" value="{{ 'rent' if intent == 'rent' else 'sale' }}">
    </div>
    <div class="col-md-4"><label>Seller Type</label>
      <select class="form-select" name="seller_type">
        <option value="">—</option>
        {% for st in ['owner','broker','developer'] %}
        <option value="{{ st }}" {% if property and property.seller_type == st %}selected{% endif %}>{{ st|title }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-4"><label>Creation Source</label>
      <select class="form-select" name="creation_source">
        <option value="admin" {% if not property or property.creation_source == 'admin' %}selected{% endif %}>Admin</option>
        <option value="user_submission" {% if property and property.creation_source == 'user_submission' %}selected{% endif %}>User Submission</option>
      </select>
    </div>
    <div class="col-md-4 form-check mt-4">
      <input type="checkbox" class="form-check-input" name="is_featured" id="feat" {% if property and property.is_featured %}checked{% endif %}>
      <label class="form-check-label" for="feat">Featured</label>
    </div>
    <div class="col-md-4">
      <label>Selected Photos List</label>
      <input type="file" class="form-control" id="adminImagesInput" name="images" multiple accept="image/*">
      <div id="adminImagesPreview" class="media-file-list media-file-list--photos d-none" aria-live="polite"></div>
    </div>
    <div class="col-md-4">
      <label>Selected Videos List</label>
      <input type="file" class="form-control" id="adminVideosInput" name="videos" multiple accept="video/*">
      <div id="adminVideosPreview" class="media-file-list media-file-list--videos d-none" aria-live="polite"></div>
    </div>
    <div class="col-md-4">
      <label>Documents (PDF)</label>
      <input type="file" class="form-control" id="adminDocsInput" name="documents" multiple accept=".pdf">
      <div id="adminDocsPreview" class="media-file-list d-none" aria-live="polite"></div>
    </div>
  </div>
  <button class="btn btn-jk-accent mt-3">Save Property</button>
</form>
<p class="small text-muted mt-2">Map marker is created automatically from latitude/longitude.</p>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/media_file_manager.js') }}"></script>
<script>
  if (window.MediaFileManager) {
    MediaFileManager.bind(document.getElementById('adminImagesInput'), document.getElementById('adminImagesPreview'), { listClass: 'media-file-list--photos' });
    MediaFileManager.bind(document.getElementById('adminVideosInput'), document.getElementById('adminVideosPreview'), { listClass: 'media-file-list--videos' });
    MediaFileManager.bind(document.getElementById('adminDocsInput'), document.getElementById('adminDocsPreview'));
  }
  (function () {
    const typeEl = document.getElementById('adminPropertyType');
    const bhkWrap = document.getElementById('adminBhkWrap');
    const bhkInput = document.getElementById('adminBhkInput');
    const intentEl = document.querySelector('select[name="listing_intent"]');
    const listingType = document.getElementById('adminListingType');
    const hide = new Set(['plot', 'land', 'shop', 'office']);
    function syncBhk() {
      const t = (typeEl?.value || '').toLowerCase();
      const show = !hide.has(t);
      bhkWrap?.classList.toggle('d-none', !show);
      if (bhkInput) bhkInput.disabled = !show;
    }
    function syncIntent() {
      if (listingType && intentEl) listingType.value = intentEl.value === 'rent' ? 'rent' : 'sale';
    }
    typeEl?.addEventListener('change', syncBhk);
    intentEl?.addEventListener('change', syncIntent);
    syncBhk();
    syncIntent();
  })();
</script>
{% endblock %}
""",
    "admin/reviews.html": """{% extends "admin/base.html" %}
{% block title %}Reviews Management{% endblock %}
{% block page_heading %}Reviews Management{% endblock %}
{% block page_subheading %}Curate testimonials, control visibility, and moderate review comments from a single workspace.{% endblock %}
{% block page_actions %}
<span class="badge bg-secondary align-self-center">{{ reviews|length }} total</span>
{% endblock %}
{% block content %}
<section class="admin-section-card">
  <h5 class="mb-3">Add New Review</h5>
  <form method="POST" action="{{ url_for('admin.add_review') }}" class="row g-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="col-md-4"><input class="form-control" name="client_name" placeholder="Client Name" required></div>
    <div class="col-md-3"><input class="form-control" name="client_location" placeholder="Location" value="Surat"></div>
    <div class="col-md-2">
      <select class="form-select" name="rating" required>
        {% for r in [5,4,3,2,1] %}<option value="{{ r }}">{{ r }} Star</option>{% endfor %}
      </select>
    </div>
    <div class="col-md-2 form-check d-flex align-items-center gap-2 mt-0">
      <input class="form-check-input" type="checkbox" name="is_active" id="isActiveNew" checked>
      <label class="form-check-label" for="isActiveNew">Active</label>
    </div>
    <div class="col-12">
      <textarea class="form-control" name="review_text" rows="3" placeholder="Review text" required></textarea>
    </div>
    <div class="col-12">
      <button class="btn btn-jk-accent">Add Review</button>
    </div>
  </form>
</section>

<section class="d-grid gap-3">
  {% for review in reviews %}
  <article class="admin-section-card">
    <form method="POST" action="{{ url_for('admin.edit_review', review_id=review.id) }}" class="row g-2">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="col-md-3"><input class="form-control" name="client_name" value="{{ review.client_name }}" required></div>
      <div class="col-md-2"><input class="form-control" name="client_location" value="{{ review.client_location }}"></div>
      <div class="col-md-2">
        <select class="form-select" name="rating">
          {% for r in [5,4,3,2,1] %}
          <option value="{{ r }}" {% if review.rating == r %}selected{% endif %}>{{ r }} Star</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2">
        <select class="form-select" name="is_active">
          <option value="1" {% if review.is_active %}selected{% endif %}>Active</option>
          <option value="0" {% if not review.is_active %}selected{% endif %}>Hidden</option>
        </select>
      </div>
      <div class="col-md-3 d-flex gap-2">
        <button class="btn btn-sm btn-outline-primary" type="submit">Save</button>
      </div>
      <div class="col-12">
        <textarea class="form-control" name="review_text" rows="2" required>{{ review.review_text }}</textarea>
      </div>
    </form>

    <div class="d-flex justify-content-between align-items-center mt-3">
      <div class="small text-muted">
        Review #{{ review.id }} • Created: {{ review.created_at }}
      </div>
      <form method="POST" action="{{ url_for('admin.delete_review', review_id=review.id) }}" onsubmit="return confirm('Delete this review and all comments?')">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <button class="btn btn-sm btn-outline-danger">Delete Review</button>
      </form>
    </div>

    <hr class="my-3">
    <h6 class="mb-2">Comments ({{ review.comments|length }})</h6>
    {% if review.comments %}
    <div class="admin-table-wrap table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>Name</th>
            <th>Comment</th>
            <th>Date</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {% for comment in review.comments %}
          <tr>
            <td>{{ comment.commenter_name }}</td>
            <td>{{ comment.comment_text }}</td>
            <td>{{ comment.created_at }}</td>
            <td>
              <form method="POST" action="{{ url_for('admin.delete_review_comment', comment_id=comment.id) }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button class="btn btn-sm btn-outline-danger">Remove</button>
              </form>
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    {% else %}
    <p class="small text-muted mb-0">No comments yet.</p>
    {% endif %}
  </article>
  {% else %}
  <p class="text-muted">No reviews available.</p>
  {% endfor %}
</section>
{% endblock %}
""",
    "admin/sell_properties.html": """{% extends "admin/base.html" %}
{% block title %}Sell Properties{% endblock %}
{% block page_heading %}Sell Properties{% endblock %}
{% block page_subheading %}Review user-uploaded sell listings, approve for public display, and manage owner submissions.{% endblock %}
{% block page_actions %}
<a
  class="btn btn-outline-secondary btn-sm"
  target="_blank"
  href="{{ url_for('admin.print_sell_properties', period=period_filter, status=status_filter if status_filter != 'all' else '', area=area_filter if area_filter else None, seller_type=seller_type_filter if seller_type_filter else None) }}"
>
  <i class="bi bi-printer me-1"></i>Print View
</a>
{% endblock %}
{% block content %}
<section class="kpi-grid mb-3">
  {% for value, label in periods %}
  <article class="admin-kpi-card {% if period_filter == value %}kpi-highlight{% endif %}">
    <div class="kpi-top">
      <p class="kpi-label">{{ label }}</p>
      <span class="kpi-icon"><i class="bi bi-calendar3"></i></span>
    </div>
    <h3 class="kpi-value">{{ period_stats.get(value, 0) }}</h3>
    <p class="kpi-meta mb-2">{{ period_stats.get(value, 0) }} sell propert{{ 'y' if period_stats.get(value, 0) == 1 else 'ies' }} in this {{ label|lower }} period</p>
    <a href="{{ url_for('admin.sell_properties', period=value, status=status_filter, area=area_filter if area_filter else None, seller_type=seller_type_filter if seller_type_filter else None) }}" class="btn btn-sm btn-light">View {{ label }}</a>
  </article>
  {% endfor %}
</section>

<div class="admin-filter-bar mb-2 d-flex flex-wrap align-items-center gap-2">
  {% for value, label in statuses %}
  <a href="{{ url_for('admin.sell_properties', status=value, period=period_filter, area=area_filter if area_filter else None, seller_type=seller_type_filter if seller_type_filter else None) }}" class="admin-filter-chip {% if status_filter == value %}active{% endif %}">{{ label }}</a>
  {% endfor %}
  <form method="get" class="ms-auto d-flex align-items-center gap-2 flex-wrap">
    <input type="hidden" name="status" value="{{ status_filter }}">
    <input type="hidden" name="period" value="{{ period_filter }}">
    <label class="form-label mb-0 small text-muted" for="areaFilter">Area</label>
    <select class="form-select form-select-sm" id="areaFilter" name="area" onchange="this.form.submit()" style="min-width: 140px;">
      <option value="">All areas</option>
      {% for area in area_options %}
      <option value="{{ area }}" {% if area_filter == area %}selected{% endif %}>{{ area }}</option>
      {% endfor %}
    </select>
    <label class="form-label mb-0 small text-muted" for="sellerTypeFilter">Seller Type</label>
    <select class="form-select form-select-sm" id="sellerTypeFilter" name="seller_type" onchange="this.form.submit()" style="min-width: 140px;">
      <option value="">All</option>
      <option value="owner" {% if seller_type_filter == 'owner' %}selected{% endif %}>Owner</option>
      <option value="broker" {% if seller_type_filter == 'broker' %}selected{% endif %}>Broker</option>
      <option value="developer" {% if seller_type_filter == 'developer' %}selected{% endif %}>Developer</option>
    </select>
  </form>
</div>

<div class="admin-table-wrap table-responsive">
  <table class="table align-middle">
    <thead>
      <tr>
        <th>#</th>
        <th>Owner / Contact</th>
        <th>Property Details</th>
        <th>Listing Intent</th>
        <th>Media</th>
        <th>Price</th>
        <th>Status</th>
        <th>Submitted</th>
        <th style="min-width: 300px;">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for submission in submissions %}
      <tr id="submission-{{ submission.id }}">
        <td>{{ submission.id }}</td>
        <td>
          <div class="fw-semibold">{{ submission.display_owner_name or submission.owner_name }}</div>
          <div class="small">
            <a href="tel:{{ submission.owner_mobile }}">{{ submission.owner_mobile }}</a>
            {% if submission.owner_alt_mobile %}
            <span class="text-muted"> / {{ submission.owner_alt_mobile }}</span>
            {% endif %}
          </div>
          {% if submission.owner_email %}
          <div class="small">
            <a href="mailto:{{ submission.owner_email }}">{{ submission.owner_email }}</a>
          </div>
          {% endif %}
          <div class="small text-muted mt-1">{{ submission.owner_address }}</div>
        </td>
        <td>
          <div class="fw-semibold">{{ submission.property_title }}</div>
          <div class="small text-muted">
            {{ submission.property_type|title }}{% if submission.bhk %} • {{ submission.bhk }} BHK{% endif %}
            {% if submission.area_sq_ft %} • {{ "%.0f"|format(submission.area_sq_ft) }} sq ft{% endif %}
            {% if submission.bungalow_number %} • #{{ submission.bungalow_number }}{% endif %}
          </div>
          <div class="small text-muted">{{ submission.property_address }}</div>
          <div class="small text-muted mb-1">{{ submission.city }}{% if submission.location_area %}, {{ submission.location_area }}{% endif %}</div>
          {% if submission.description %}
          <div class="small">{{ submission.description[:120] }}{% if submission.description|length > 120 %}…{% endif %}</div>
          {% endif %}
          {% if submission.amenities %}
          <div class="small text-muted mt-1">Amenities: {{ submission.amenities|join(', ') }}</div>
          {% endif %}
          {% if submission.property_id %}
          <a href="{{ url_for('admin.property_form', pid=submission.property_id) }}" class="btn btn-sm btn-outline-primary mt-1">
            Open Property #{{ submission.property_id }}
          </a>
          {% endif %}
        </td>
        <td>
          {% if submission.listing_intent == 'rent' %}
          <span class="badge bg-info text-dark">For Rent</span>
          {% else %}
          <span class="badge bg-success">For Sale</span>
          {% endif %}
        </td>
        <td>
          {% if submission.images %}
          <div class="d-flex flex-wrap gap-1 mb-1">
            {% for img in submission.images[:3] %}
            <img src="{{ url_for('static', filename=img) }}" alt="Property image" class="rounded border" style="width: 48px; height: 48px; object-fit: cover;">
            {% endfor %}
          </div>
          {% endif %}
          <div class="small text-muted">
            {{ submission.images|length }} image(s), {{ submission.videos|length }} video(s)
          </div>
        </td>
        <td>₹{{ "{:,.0f}".format(submission.price or 0) }}</td>
        <td>
          {% if submission.status == "pending" %}
          <span class="admin-status-pill status-pending">Pending</span>
          {% elif submission.status == "approved" %}
          <span class="admin-status-pill status-approved">Approved</span>
          {% else %}
          <span class="admin-status-pill status-rejected">Rejected</span>
          {% endif %}
          {% if submission.reviewed_at %}
          <div class="small text-muted mt-1">Reviewed: {{ submission.reviewed_at }}</div>
          {% endif %}
        </td>
        <td class="small">{{ submission.created_at }}</td>
        <td>
          <form method="POST" action="{{ url_for('admin.update_sell_property', sid=submission.id) }}" class="d-grid gap-2 mb-2">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="redirect_status" value="{{ status_filter }}">
            <input type="hidden" name="redirect_period" value="{{ period_filter }}">
            <select class="form-select form-select-sm" name="status">
              <option value="pending" {% if submission.status == 'pending' %}selected{% endif %}>Pending</option>
              <option value="approved" {% if submission.status == 'approved' %}selected{% endif %}>Approved</option>
              <option value="rejected" {% if submission.status == 'rejected' %}selected{% endif %}>Rejected</option>
            </select>
            <input
              type="text"
              name="review_note"
              class="form-control form-control-sm"
              maxlength="250"
              placeholder="Review note (optional)"
              value="{{ submission.review_note or '' }}"
            >
            <button class="btn btn-sm btn-jk-accent">Save</button>
          </form>
          <div class="d-flex flex-wrap gap-1">
            <a href="{{ url_for('admin.edit_sell_property', sid=submission.id, status=status_filter, period=period_filter) }}" class="btn btn-sm btn-outline-primary">Edit</a>
            <form method="POST" action="{{ url_for('admin.delete_sell_property', sid=submission.id) }}" class="d-inline" onsubmit="return confirm('Delete this sell property submission?');">
              <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
              <input type="hidden" name="redirect_status" value="{{ status_filter }}">
              <input type="hidden" name="redirect_period" value="{{ period_filter }}">
              <button class="btn btn-sm btn-outline-danger">Delete</button>
            </form>
          </div>
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="8" class="text-center text-muted py-4">No sell property submissions for this filter.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""",
    "admin/sell_properties_print.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Sell Properties Print</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    @media print {
      .no-print { display: none !important; }
      body { margin: 0; }
    }
  </style>
</head>
<body class="p-3">
  <div class="d-flex justify-content-between align-items-center mb-3 no-print">
    <h4 class="mb-0">Sell Properties Report</h4>
    <button class="btn btn-dark btn-sm" onclick="window.print()">Print</button>
  </div>
  <div class="mb-2 small text-muted">
    Period: {{ period_filter|title }} | Dates: {{ start_date }} to {{ end_date }} | Status: {{ status_filter|title }}
  </div>
  <table class="table table-sm table-bordered align-middle">
    <thead class="table-light">
      <tr>
        <th>ID</th>
        <th>Submitted</th>
        <th>Owner</th>
        <th>Contact</th>
        <th>Property</th>
        <th>Address</th>
        <th>Price</th>
        <th>Status</th>
        <th>Note</th>
      </tr>
    </thead>
    <tbody>
      {% for submission in submissions %}
      <tr>
        <td>{{ submission.id }}</td>
        <td>{{ submission.created_at }}</td>
        <td>{{ submission.owner_name }}</td>
        <td>
          {{ submission.owner_mobile }}
          {% if submission.owner_alt_mobile %} / {{ submission.owner_alt_mobile }}{% endif %}
          {% if submission.owner_email %}<br>{{ submission.owner_email }}{% endif %}
        </td>
        <td>
          {{ submission.property_title }}
          ({{ submission.property_type|title }}{% if submission.bhk %}, {{ submission.bhk }} BHK{% endif %})
        </td>
        <td>{{ submission.property_address }}, {{ submission.city }}</td>
        <td>₹{{ "{:,.0f}".format(submission.price or 0) }}</td>
        <td>{{ submission.status|title }}</td>
        <td>{{ submission.review_note or '-' }}</td>
      </tr>
      {% else %}
      <tr>
        <td colspan="9" class="text-center">No sell property submissions available.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</body>
</html>
""",
    "admin/sell_property_edit.html": """{% extends "admin/base.html" %}
{% block title %}Edit Sell Property{% endblock %}
{% block page_heading %}Edit Sell Property #{{ submission.id }}{% endblock %}
{% block page_subheading %}Update owner contact details and property information for this user submission.{% endblock %}
{% block content %}
<section class="admin-section-card">
  <form method="POST" class="row g-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="col-12"><h5 class="mb-0">Owner Information</h5></div>
    <div class="col-md-6">
      <label class="form-label">Owner Name *</label>
      <input class="form-control" name="owner_name" value="{{ submission.owner_name }}" required>
    </div>
    <div class="col-md-3">
      <label class="form-label">Mobile *</label>
      <input class="form-control" name="owner_mobile" value="{{ submission.owner_mobile }}" required>
    </div>
    <div class="col-md-3">
      <label class="form-label">Alt Mobile</label>
      <input class="form-control" name="owner_alt_mobile" value="{{ submission.owner_alt_mobile or '' }}">
    </div>
    <div class="col-md-6">
      <label class="form-label">Email</label>
      <input type="email" class="form-control" name="owner_email" value="{{ submission.owner_email or '' }}">
    </div>
    <div class="col-md-6">
      <label class="form-label">Owner Address *</label>
      <input class="form-control" name="owner_address" value="{{ submission.owner_address }}" required>
    </div>

    <div class="col-12 mt-2"><h5 class="mb-0">Property Details</h5></div>
    <div class="col-md-8">
      <label class="form-label">Property Title *</label>
      <input class="form-control" name="property_title" value="{{ submission.property_title }}" required>
    </div>
    <div class="col-md-4">
      <label class="form-label">Property Type *</label>
      <select class="form-select" name="property_type" required>
        {% for t in ['flat', 'apartment', 'bungalow', 'villa', 'plot', 'commercial', 'shop', 'office'] %}
        <option value="{{ t }}" {% if submission.property_type == t %}selected{% endif %}>{{ t|title }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-3">
      <label class="form-label">BHK</label>
      <input type="number" class="form-control" name="bhk" value="{{ submission.bhk or 0 }}" min="0">
    </div>
    <div class="col-md-3">
      <label class="form-label">Area (sq ft)</label>
      <input class="form-control" name="area_sq_ft" value="{{ submission.area_sq_ft or '' }}">
    </div>
    <div class="col-md-3">
      <label class="form-label">Price (₹)</label>
      <input class="form-control" name="price" value="{{ submission.price or '' }}">
    </div>
    <div class="col-md-3">
      <label class="form-label">Bungalow #</label>
      <input class="form-control" name="bungalow_number" value="{{ submission.bungalow_number or '' }}">
    </div>
    <div class="col-md-8">
      <label class="form-label">Property Address *</label>
      <input class="form-control" name="property_address" value="{{ submission.property_address }}" required>
    </div>
    <div class="col-md-2">
      <label class="form-label">City</label>
      <input class="form-control" name="city" value="{{ submission.city or 'Surat' }}">
    </div>
    <div class="col-md-2">
      <label class="form-label">Area</label>
      <input class="form-control" name="location_area" value="{{ submission.location_area or '' }}">
    </div>
    <div class="col-12">
      <label class="form-label">Description</label>
      <textarea class="form-control" name="description" rows="3">{{ submission.description or '' }}</textarea>
    </div>
    <div class="col-12">
      <label class="form-label">Review Note</label>
      <input class="form-control" name="review_note" value="{{ submission.review_note or '' }}" maxlength="250">
    </div>

    <div class="col-12 d-flex gap-2">
      <button class="btn btn-jk-accent">Save Changes</button>
      <a href="{{ url_for('admin.sell_properties') }}" class="btn btn-outline-secondary">Cancel</a>
    </div>
  </form>
</section>
{% endblock %}
""",
    "admin/seller_print.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Seller Profile Print</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    @media print { .no-print { display: none !important; } }
  </style>
</head>
<body class="p-4">
  <div class="d-flex justify-content-between align-items-center mb-3 no-print">
    <h4 class="mb-0">Seller Profile</h4>
    <button class="btn btn-dark btn-sm" onclick="window.print()">Print</button>
  </div>
  <table class="table table-bordered">
    <tr><th style="width: 220px;">Name</th><td>{{ seller.full_name }}</td></tr>
    <tr><th>Mobile</th><td>{{ seller.mobile }}</td></tr>
    <tr><th>Email</th><td>{{ seller.email or '-' }}</td></tr>
    <tr><th>Address</th><td>{{ seller.address or '-' }}</td></tr>
    <tr><th>Tags</th><td>{{ ', '.join(seller.tags) if seller.tags else '-' }}</td></tr>
    <tr><th>Notes</th><td>{{ seller.notes or '-' }}</td></tr>
    <tr><th>Created</th><td>{{ seller.created_at }}</td></tr>
  </table>
</body>
</html>
""",
    "admin/sellers.html": """{% extends "admin/base.html" %}
{% block title %}Sellers Info{% endblock %}
{% block page_heading %}Sellers Info{% endblock %}
{% block page_subheading %}Manage seller profiles, metadata tags, and printable profile records.{% endblock %}
{% block content %}
<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>{{ 'Edit Seller Profile' if editing else 'Add Seller Profile' }}</h5>
  </div>
  <form method="POST" class="row g-3">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    {% if editing %}
    <input type="hidden" name="seller_id" value="{{ editing.id }}">
    {% endif %}
    <div class="col-md-4">
      <label>Full Name *</label>
      <input class="form-control" name="full_name" required value="{{ editing.full_name if editing else '' }}">
    </div>
    <div class="col-md-4">
      <label>Mobile *</label>
      <input class="form-control" name="mobile" required value="{{ editing.mobile if editing else '' }}">
    </div>
    <div class="col-md-4">
      <label>Email</label>
      <input type="email" class="form-control" name="email" value="{{ editing.email if editing else '' }}">
    </div>
    <div class="col-md-6">
      <label>Address</label>
      <textarea class="form-control" rows="2" name="address">{{ editing.address if editing else '' }}</textarea>
    </div>
    <div class="col-md-6">
      <label>Tags (comma separated)</label>
      <input class="form-control" name="tags_text" placeholder="vip, urgent_followup, premium" value="{{ editing.tags_text if editing else '' }}">
    </div>
    <div class="col-12">
      <label>Notes</label>
      <textarea class="form-control" rows="3" name="notes">{{ editing.notes if editing else '' }}</textarea>
    </div>
    <div class="col-12 d-flex gap-2">
      <button class="btn btn-jk-accent">{{ 'Update Seller' if editing else 'Add Seller' }}</button>
      {% if editing %}
      <a href="{{ url_for('admin.sellers') }}" class="btn btn-outline-secondary">Cancel Edit</a>
      {% endif %}
    </div>
  </form>
</section>

<section class="admin-section-card">
  <div class="admin-section-heading">
    <h5>Seller Profiles</h5>
    <form method="GET" class="d-flex gap-2">
      <input class="form-control form-control-sm" name="q" value="{{ query }}" placeholder="Search seller">
      <button class="btn btn-sm btn-outline-secondary">Search</button>
    </form>
  </div>
  <div class="admin-table-wrap table-responsive">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>Name</th>
          <th>Contact</th>
          <th>Tags</th>
          <th>Notes</th>
          <th>Created</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {% for seller in sellers %}
        <tr>
          <td class="fw-semibold">{{ seller.full_name }}</td>
          <td>
            <div>{{ seller.mobile }}</div>
            <div class="small text-muted">{{ seller.email or '-' }}</div>
          </td>
          <td>{{ ', '.join(seller.tags) if seller.tags else '-' }}</td>
          <td>{{ seller.notes or '-' }}</td>
          <td>{{ seller.created_at }}</td>
          <td class="text-nowrap">
            <a class="btn btn-sm btn-outline-primary" href="{{ url_for('admin.sellers', edit=seller.id) }}">Edit</a>
            <a class="btn btn-sm btn-outline-secondary" target="_blank" href="{{ url_for('admin.print_seller', seller_id=seller.id) }}">Print</a>
            <a class="btn btn-sm btn-outline-dark" href="{{ url_for('admin.seller_pdf', seller_id=seller.id) }}">PDF</a>
          </td>
        </tr>
        {% else %}
        <tr>
          <td colspan="6" class="text-center text-muted py-4">No seller profiles found.</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</section>
{% endblock %}
""",
    "admin/submissions.html": """{% extends "admin/base.html" %}
{% block title %}Owner Submissions{% endblock %}
{% block page_heading %}Owner Submissions{% endblock %}
{% block page_subheading %}Review owner-uploaded listings, approve quality submissions, and keep publishing flow moving.{% endblock %}
{% block content %}
<div class="admin-filter-bar mb-2">
  {% for value, label in statuses %}
  <a href="{{ url_for('admin.submissions', status=value) }}" class="admin-filter-chip {% if status_filter == value %}active{% endif %}">{{ label }}</a>
  {% endfor %}
</div>

<div class="admin-table-wrap table-responsive">
  <table class="table align-middle">
    <thead>
      <tr>
        <th>#</th>
        <th>Owner</th>
        <th>Property</th>
        <th>Price</th>
        <th>Status</th>
        <th>Submitted</th>
        <th style="min-width: 300px;">Actions</th>
      </tr>
    </thead>
    <tbody>
      {% for submission in submissions %}
      <tr id="submission-{{ submission.id }}">
        <td>{{ submission.id }}</td>
        <td>
          <div class="fw-semibold">{{ submission.owner_name }}</div>
          <div class="small">
            <a href="tel:{{ submission.owner_mobile }}">{{ submission.owner_mobile }}</a>
          </div>
          {% if submission.owner_email %}
          <div class="small">
            <a href="mailto:{{ submission.owner_email }}">{{ submission.owner_email }}</a>
          </div>
          {% endif %}
        </td>
        <td>
          <div class="fw-semibold">{{ submission.property_title }}</div>
          <div class="small text-muted">
            {{ submission.property_type|title }}{% if submission.bhk %} • {{ submission.bhk }} BHK{% endif %}
            {% if submission.area_sq_ft %} • {{ "%.0f"|format(submission.area_sq_ft) }} sq ft{% endif %}
          </div>
          <div class="small text-muted mb-1">{{ submission.city }}{% if submission.location_area %}, {{ submission.location_area }}{% endif %}</div>
          {% if submission.property_id %}
          <a href="{{ url_for('admin.property_form', pid=submission.property_id) }}" class="btn btn-sm btn-outline-primary">
            Open Property
          </a>
          {% endif %}
        </td>
        <td>₹{{ "{:,.0f}".format(submission.price or 0) }}</td>
        <td>
          {% if submission.status == "pending" %}
          <span class="admin-status-pill status-pending">Pending</span>
          {% elif submission.status == "approved" %}
          <span class="admin-status-pill status-approved">Approved</span>
          {% else %}
          <span class="admin-status-pill status-rejected">Rejected</span>
          {% endif %}
          <div class="small text-muted mt-1">
            {{ submission.images|length }} image(s), {{ submission.videos|length }} video(s)
          </div>
        </td>
        <td class="small">{{ submission.created_at }}</td>
        <td>
          {% if submission.status == "pending" %}
          <form method="POST" action="{{ url_for('admin.approve_submission', sid=submission.id) }}" class="d-grid gap-2 mb-2">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="redirect_status" value="{{ status_filter }}">
            <input
              type="text"
              name="review_note"
              class="form-control form-control-sm"
              maxlength="250"
              placeholder="Approval note (optional)"
            >
            <button class="btn btn-sm btn-success">Approve Submission</button>
          </form>
          <form method="POST" action="{{ url_for('admin.reject_submission', sid=submission.id) }}" class="d-grid gap-2">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <input type="hidden" name="redirect_status" value="{{ status_filter }}">
            <input
              type="text"
              name="review_note"
              class="form-control form-control-sm"
              maxlength="250"
              placeholder="Rejection reason (optional)"
            >
            <button class="btn btn-sm btn-outline-danger">Reject Submission</button>
          </form>
          {% else %}
          <div class="small text-muted mb-1">
            Reviewed by: {{ submission.reviewed_by or "Admin" }}
          </div>
          {% if submission.review_note %}
          <div class="small">Note: {{ submission.review_note }}</div>
          {% endif %}
          {% endif %}
        </td>
      </tr>
      {% else %}
      <tr>
        <td colspan="7" class="text-center text-muted py-4">No submissions found for this filter.</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
""",
    "admin/utilities.html": """{% extends "admin/base.html" %}
{% block title %}Utilities{% endblock %}
{% block page_heading %}Admin Utilities{% endblock %}
{% block page_subheading %}Super-admin utility controls for safe cleanup of mock/test data only.{% endblock %}
{% block content %}
<section class="admin-section-card">
  <div class="alert alert-warning mb-3">
    This utility removes <strong>mock/demo/test</strong> rows from selected operational tables.
    It does <strong>not</strong> drop tables or reset schema.
  </div>
  <div class="admin-table-wrap table-responsive mb-3">
    <table class="table align-middle">
      <thead>
        <tr>
          <th>Table</th>
          <th>Detected Mock Rows</th>
        </tr>
      </thead>
      <tbody>
        {% for table, count in counts.items() %}
        <tr>
          <td class="fw-semibold">{{ table }}</td>
          <td>{{ count }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  <form method="POST" action="{{ url_for('admin.flush_mock_data') }}">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <button class="btn btn-outline-danger" onclick="return confirm('Run mock-data flush now?')">
      <i class="bi bi-trash3 me-1"></i>Flush Mock Data
    </button>
  </form>
</section>
{% endblock %}
""",
    "admin/verify_otp.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Admin Verification - {{ company_name }}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/admin.css') }}" rel="stylesheet">
</head>
<body class="admin-login-page">
  <div class="admin-login-shell">
    <section class="admin-login-intro">
      <span class="admin-login-chip">Two-Factor Security</span>
      <h1>{{ company_name }}</h1>
      <p>Password verified for <strong>{{ pending_admin.username }}</strong>. Complete OTP verification to access admin tools.</p>
      <ul class="admin-login-feature-list">
        <li><i class="bi bi-shield-lock"></i> Password + OTP required</li>
        <li><i class="bi bi-person-lock"></i> Role and permission checks enforced</li>
        <li><i class="bi bi-lock"></i> Sensitive routes require verified session</li>
      </ul>
    </section>

    <section class="admin-login-card">
      <div class="text-center mb-4">
        <span class="admin-login-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" class="jk-logo jk-logo-mark" alt="{{ company_name }}">
        </span>
        <h4 class="mt-3 mb-1">OTP Verification</h4>
        <p class="text-muted mb-0">Choose an available method to continue</p>
      </div>

      {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
      <div class="alert alert-{{ cat }}">{{ msg }}</div>
      {% endfor %}
      {% endwith %}

      {% if dev_otp %}
      <div class="alert alert-warning small">
        <strong>Development fallback active:</strong> OTP code is <code>{{ dev_otp }}</code>.
      </div>
      {% endif %}

      {% if show_totp %}
      <form method="POST" class="admin-login-form mb-3">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="action" value="verify_totp">
        <label for="totp_code">Authenticator Code</label>
        <input id="totp_code" class="form-control mb-2" name="totp_code" autocomplete="one-time-code" placeholder="6-digit code" required>
        <button class="btn btn-jk-accent w-100">Verify with Google Authenticator</button>
      </form>
      {% endif %}

      {% if show_mobile %}
      <form method="POST" class="admin-login-form mb-2">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="action" value="verify_mobile">
        <label for="mobile_otp">Mobile OTP Code</label>
        <input id="mobile_otp" class="form-control mb-2" name="mobile_otp" autocomplete="one-time-code" placeholder="OTP from SMS" required>
        <button class="btn btn-outline-dark w-100">Verify Mobile OTP</button>
      </form>
      <form method="POST">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="hidden" name="action" value="resend_mobile">
        <button class="btn btn-link p-0">Resend mobile OTP</button>
      </form>
      {% endif %}

      {% if not show_totp and not show_mobile %}
      <div class="alert alert-danger">No OTP method is available for this account. Contact super admin.</div>
      {% endif %}
    </section>
  </div>
</body>
</html>
""",
    "admin/visit_print.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>JAKKASH — Customer Visit</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body { font-family: Georgia, "Times New Roman", serif; color: #1f1f24; }
    .brand { letter-spacing: 0.08em; font-weight: 700; color: #e67e22; }
    .sheet { max-width: 860px; margin: 0 auto; border: 1px solid #ddd; padding: 2rem 2.25rem; }
    .meta-table th { width: 220px; background: #faf7f4; }
    .signature-row { display: flex; gap: 2rem; margin-top: 1.5rem; }
    .signature-col { flex: 1 1 0; min-width: 0; }
    .signature-line {
      height: 60px;
      border-bottom: 1px solid #333;
      margin-top: 0.35rem;
      display: flex;
      align-items: flex-end;
      justify-content: flex-start;
      overflow: hidden;
    }
    .signature-line img { max-height: 56px; max-width: 100%; object-fit: contain; }
    @media print {
      .no-print { display: none !important; }
      body { background: #fff; }
      .sheet { border: 0; padding: 0; }
      .signature-row { page-break-inside: avoid; }
    }
    @media (max-width: 767.98px) {
      .signature-row { flex-direction: column; gap: 1.25rem; }
    }
  </style>
</head>
<body class="p-4 bg-light">
  <div class="sheet bg-white">
    <div class="d-flex justify-content-between align-items-start mb-4 no-print">
      <div>
        <div class="brand">JAKKASH PROPERTY CONSULTANCY</div>
        <div class="text-muted small">Customer Visit Record</div>
      </div>
      <button class="btn btn-dark btn-sm" onclick="window.print()">Print / Save PDF</button>
    </div>
    <header class="mb-4 border-bottom pb-3">
      <div class="brand fs-4">JAKKASH PROPERTY CONSULTANCY</div>
      <div class="text-muted">Surat · Brokerage Site Visit Form</div>
    </header>
    <table class="table table-bordered meta-table">
      <tr><th>Visit Date</th><td>{{ visit.visit_date }}</td></tr>
      <tr><th>Client Name</th><td>{{ visit.client_name }}</td></tr>
      <tr><th>Client Address</th><td>{{ visit.client_address }}</td></tr>
      <tr><th>Client Contact</th><td>{{ visit.client_contact }}</td></tr>
      <tr><th>Client Requirement</th><td>{{ visit.client_requirement }}</td></tr>
      <tr><th>Executive Name</th><td>{{ visit.executive_name or '-' }}</td></tr>
      <tr><th>Executive Address</th><td>{{ visit.executive_address or '-' }}</td></tr>
      <tr><th>Executive Contact</th><td>{{ visit.executive_contact or '-' }}</td></tr>
    </table>

    <h6 class="mt-4 mb-2">Selected Properties</h6>
    <table class="table table-bordered table-sm">
      <thead>
        <tr>
          <th>Title</th>
          <th>Area</th>
          <th>Block / Unit</th>
          <th>Price / Rent</th>
        </tr>
      </thead>
      <tbody>
        {% if visit.selected_properties %}
          {% for p in visit.selected_properties %}
          <tr>
            <td>{{ p.property_name }}</td>
            <td>{{ p.area_name or '-' }}</td>
            <td>{% if p.block_wing or p.unit_number %}{{ p.block_wing or '' }}{% if p.block_wing and p.unit_number %} / {% endif %}{{ p.unit_number or '' }}{% else %}-{% endif %}</td>
            <td>₹{{ "{:,.0f}".format(p.price or 0) }}{% if (p.listing_intent or p.listing_type) == 'rent' %}/mo{% endif %}</td>
          </tr>
          {% endfor %}
        {% else %}
          <tr>
            <td colspan="4">{{ visit.property_names_display or visit.property_name or ('Property #' ~ visit.property_id) }}</td>
          </tr>
        {% endif %}
      </tbody>
    </table>

    <div class="signature-row">
      <div class="signature-col">
        <strong>Customer Signature</strong>
        <div class="signature-line">
          {% if visit.customer_signature_data %}
          <img src="{{ visit.customer_signature_data }}" alt="Customer Signature">
          {% endif %}
        </div>
        <div class="small text-muted mt-1">{{ visit.customer_signature_label or 'Customer signature pending' }}</div>
      </div>
      <div class="signature-col">
        <strong>Executive / Broker Signature</strong>
        <div class="signature-line">
          {% if visit.executive_signature_data %}
          <img src="{{ visit.executive_signature_data }}" alt="Executive Signature">
          {% endif %}
        </div>
        <div class="small text-muted mt-1">{{ visit.executive_signature_label or 'Executive signature pending' }}</div>
      </div>
    </div>
    <footer class="mt-4 pt-3 border-top small text-muted">
      Generated for internal brokerage use · JAKKASH Property Consultancy
    </footer>
  </div>
</body>
</html>
""",
    "base.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{{ app_name }}{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
  {% block extra_css %}{% endblock %}
</head>
<body>
  <nav class="navbar">
    <div class="container nav-inner">
      <a href="{{ url_for('main.index') }}" class="logo">🏠 {{ app_name }}</a>
      <ul class="nav-links">
        <li><a href="{{ url_for('main.index') }}">Home</a></li>
        <li><a href="{{ url_for('main.search_page') }}">Search</a></li>
        <li><a href="{{ url_for('main.compare_page') }}">Compare</a></li>
        <li><a href="{{ url_for('main.emi_page') }}">EMI</a></li>
        <li><a href="{{ url_for('main.chat_page') }}">Property Assistant</a></li>
        {% if current_user.is_authenticated %}
          <li><a href="{{ url_for('main.schedule_visit_page') }}">Visits</a></li>
          {% if current_user.is_admin %}
            <li><a href="{{ url_for('admin.dashboard') }}">Admin</a></li>
          {% endif %}
          <li><span class="user-badge">{{ current_user.username }}</span></li>
          <li><a href="{{ url_for('auth.logout') }}">Logout</a></li>
        {% else %}
          <li><a href="{{ url_for('auth.login') }}">Login</a></li>
          <li><a href="{{ url_for('auth.register') }}" class="btn btn-sm">Register</a></li>
        {% endif %}
      </ul>
    </div>
  </nav>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <div class="container flash-container">
        {% for category, message in messages %}
          <div class="alert alert-{{ category }}">{{ message }}</div>
        {% endfor %}
      </div>
    {% endif %}
  {% endwith %}

  <main class="main-content">
    {% block content %}{% endblock %}
  </main>

  <footer class="footer">
    <div class="container">
      <p>&copy; 2025 {{ app_name }} — Smart property search powered by AI</p>
    </div>
  </footer>

  <script src="{{ url_for('static', filename='js/main.js') }}"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
""",
    "chat.html": """{% extends "base.html" %}
{% block title %}Property Assistant — {{ app_name }}{% endblock %}
{% block content %}
<div class="container section chat-page">
  <h1>JAKKASH Property Assistant</h1>
  <p class="subtitle">Menu-guided help for search, listings, broker contact, and FAQs.</p>
  <div class="chat-container card">
    <div id="chatMessages" class="chat-messages">
      <div class="chat-msg assistant">
        <div class="bubble">Welcome to JAKKASH Property Assistant. Use the options below or open the full assistant.</div>
      </div>
    </div>
    <form id="chatForm" class="chat-input-row">
      <input type="text" id="chatInput" placeholder="e.g. Find 2BHK apartments in Bangalore" autocomplete="off" required>
      <button type="submit" class="btn btn-primary">Send</button>
    </form>
  </div>
  <div class="chat-suggestions">
    <button type="button" class="chip" data-msg="Show apartments in Mumbai">Mumbai apartments</button>
    <button type="button" class="chip" data-msg="Recommend properties under 1 crore">Recommendations</button>
    <button type="button" class="chip" data-msg="Predict price for 1500 sqft in Bangalore">Price prediction</button>
    <button type="button" class="chip" data-msg="Calculate EMI for 5000000 at 8.5% for 20 years">EMI calculator</button>
  </div>
</div>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/chat.js') }}"></script>
{% endblock %}
""",
    "compare.html": """{% extends "base.html" %}
{% block title %}Compare — {{ app_name }}{% endblock %}
{% block content %}
<div class="container section">
  <h1>Property Comparison</h1>
  <p>Enter up to 4 property IDs (comma-separated) or select from search results.</p>
  <form id="compareForm" class="card compare-form">
    <div class="form-group">
      <label>Property IDs</label>
      <input type="text" id="compareIds" placeholder="e.g. 1,2,3" value="{{ request.args.get('ids', '') }}">
    </div>
    <button type="submit" class="btn btn-primary">Compare</button>
  </form>
  <div id="compareTable" class="compare-table-wrap mt-2"></div>
</div>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/compare.js') }}"></script>
{% endblock %}
""",
    "emi.html": """{% extends "base.html" %}
{% block title %}EMI Calculator — {{ app_name }}{% endblock %}
{% block content %}
<div class="container section">
  <h1>Home Loan EMI Calculator</h1>
  <div class="emi-layout">
    <form id="emiForm" class="card emi-form">
      <div class="form-group">
        <label>Loan Amount (₹)</label>
        <input type="number" id="principal" value="5000000" min="100000" step="100000" required>
      </div>
      <div class="form-group">
        <label>Annual Interest Rate (%)</label>
        <input type="number" id="annual_rate" value="8.5" min="1" max="30" step="0.1" required>
      </div>
      <div class="form-group">
        <label>Tenure (years)</label>
        <input type="number" id="tenure_years" value="20" min="1" max="30" required>
      </div>
      <button type="submit" class="btn btn-primary btn-block">Calculate EMI</button>
    </form>
    <div id="emiResult" class="card emi-result">
      <h3>Results</h3>
      <p class="emi-highlight">Monthly EMI: <span id="emiValue">—</span></p>
      <ul id="emiBreakdown" class="emi-breakdown"></ul>
    </div>
  </div>
</div>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/emi.js') }}"></script>
{% endblock %}
""",
    "index.html": """{% extends "base.html" %}
{% block title %}Home — {{ app_name }}{% endblock %}
{% block content %}
<section class="hero">
  <div class="container">
    <h1>Find Your Dream Property</h1>
    <p>Search, compare, predict prices, calculate EMI, and use our Property Assistant for guided help.</p>
    <div class="hero-actions">
      <a href="{{ url_for('main.search_page') }}" class="btn btn-primary">Search Properties</a>
      <a href="{{ url_for('main.chat_page') }}" class="btn btn-outline">Property Assistant</a>
    </div>
  </div>
</section>

<section class="container section">
  <h2>Featured Listings</h2>
  <div id="recommendations" class="property-grid">
    {% for p in properties %}
    <article class="property-card">
      <div class="card-image">
        {% if p.image_url %}
        <img src="/{{ p.image_url }}" alt="{{ p.title }}">
        {% else %}
        <div class="placeholder-img">🏢</div>
        {% endif %}
      </div>
      <div class="card-body">
        <span class="badge">{{ p.property_type }}</span>
        <h3><a href="{{ url_for('main.property_detail', property_id=p.id) }}">{{ p.title }}</a></h3>
        <p class="location">{{ p.locality }}, {{ p.city }}</p>
        <p class="price">₹{{ "{:,.0f}".format(p.price) }}</p>
        <p class="meta">{{ p.bedrooms }} BHK · {{ p.area_sqft }} sqft</p>
      </div>
    </article>
    {% endfor %}
  </div>
</section>

<section class="container section features">
  <h2>What We Offer</h2>
  <div class="feature-grid">
    <div class="feature-card"><h3>🔍 Property Search</h3><p>Filter by city, type, budget, and bedrooms.</p></div>
    <div class="feature-card"><h3>✨ AI Recommendations</h3><p>Personalized picks based on your preferences.</p></div>
    <div class="feature-card"><h3>📈 Price Prediction</h3><p>Random Forest ML estimates fair market value.</p></div>
    <div class="feature-card"><h3>💰 EMI Calculator</h3><p>Plan your home loan with instant EMI breakdown.</p></div>
    <div class="feature-card"><h3>⚖️ Compare</h3><p>Side-by-side comparison of up to 4 properties.</p></div>
    <div class="feature-card"><h3>📅 Site Visits</h3><p>Schedule tours with one click.</p></div>
  </div>
</section>
{% endblock %}
{% block extra_js %}
<script>
  fetch('/api/recommend').then(r => r.json()).then(d => {
    if (d.success && d.properties.length) console.log('Recommendations loaded', d.properties.length);
  });
</script>
{% endblock %}
""",
    "login.html": """{% extends "base.html" %}
{% block title %}Login — {{ app_name }}{% endblock %}
{% block content %}
<div class="container auth-container">
  <div class="auth-card">
    <h1>Login</h1>
    <form method="POST" action="{{ url_for('auth.login') }}">
      <div class="form-group">
        <label for="username">Username</label>
        <input type="text" id="username" name="username" required autofocus>
      </div>
      <div class="form-group">
        <label for="password">Password</label>
        <input type="password" id="password" name="password" required>
      </div>
      <button type="submit" class="btn btn-primary btn-block">Login</button>
    </form>
    <p class="auth-footer">No account? <a href="{{ url_for('auth.register') }}">Register</a></p>
    <p class="text-muted small">Use credentials provisioned by your administrator.</p>
  </div>
</div>
{% endblock %}
""",
    "property_detail.html": """{% extends "base.html" %}
{% block title %}{{ property.title }} — {{ app_name }}{% endblock %}
{% block content %}
<div class="container section property-detail">
  <div class="detail-grid">
    <div class="detail-gallery">
      {% if images %}
        {% for img in images %}
        <img src="/{{ img.image_path }}" alt="{{ property.title }}">
        {% endfor %}
      {% elif property.image_url %}
        <img src="/{{ property.image_url }}" alt="{{ property.title }}" class="main-img">
      {% else %}
        <div class="placeholder-img large">🏢</div>
      {% endif %}
    </div>
    <div class="detail-info card">
      <span class="badge">{{ property.property_type }}</span>
      <span class="badge badge-rent">{{ property.listing_type }}</span>
      <h1>{{ property.title }}</h1>
      <p class="location">{{ property.locality }}, {{ property.city }}</p>
      <p class="price large">₹{{ "{:,.0f}".format(property.price) }}</p>
      <ul class="specs">
        <li>{{ property.bedrooms }} Bedrooms</li>
        <li>{{ property.bathrooms }} Bathrooms</li>
        <li>{{ property.area_sqft }} sqft</li>
        {% if property.year_built %}<li>Built {{ property.year_built }}</li>{% endif %}
      </ul>
      {% if property.amenities %}
      <div class="amenities">
        <h3>Amenities</h3>
        {% for a in property.amenities %}
        <span class="tag">{{ a }}</span>
        {% endfor %}
      </div>
      {% endif %}
      <p>{{ property.description }}</p>
      <div class="detail-actions">
        <a href="{{ url_for('main.compare_page') }}?ids={{ property.id }}" class="btn btn-outline">Add to Compare</a>
        {% if current_user.is_authenticated %}
        <button class="btn btn-primary" onclick="openVisitModal({{ property.id }}, '{{ property.title|e }}')">Schedule Visit</button>
        {% else %}
        <a href="{{ url_for('auth.login') }}" class="btn btn-primary">Login to Schedule Visit</a>
        {% endif %}
      </div>
    </div>
  </div>
</div>

<div id="visitModal" class="modal hidden">
  <div class="modal-content card">
    <h3>Schedule Site Visit</h3>
    <p id="visitPropertyTitle"></p>
    <form id="visitForm">
      <input type="hidden" id="visit_property_id">
      <div class="form-group"><label>Date</label><input type="date" id="visit_date" required></div>
      <div class="form-group"><label>Time</label><input type="time" id="visit_time" required></div>
      <div class="form-group"><label>Notes</label><textarea id="visit_notes"></textarea></div>
      <button type="submit" class="btn btn-primary">Submit</button>
      <button type="button" class="btn btn-outline" onclick="closeVisitModal()">Cancel</button>
    </form>
  </div>
</div>
{% endblock %}
{% block extra_js %}
<script>
function openVisitModal(id, title) {
  document.getElementById('visit_property_id').value = id;
  document.getElementById('visitPropertyTitle').textContent = title;
  document.getElementById('visitModal').classList.remove('hidden');
}
function closeVisitModal() {
  document.getElementById('visitModal').classList.add('hidden');
}
document.getElementById('visitForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const res = await fetch('/api/visits', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      property_id: document.getElementById('visit_property_id').value,
      visit_date: document.getElementById('visit_date').value,
      visit_time: document.getElementById('visit_time').value,
      notes: document.getElementById('visit_notes').value
    })
  });
  const d = await res.json();
  alert(d.message || d.error);
  if (d.success) closeVisitModal();
});
</script>
{% endblock %}
""",
    "public/404.html": """﻿{% extends "public/base.html" %}
{% block content %}
<div class="container py-5 text-center scroll-reveal">
  <h1>404</h1>
  <p>Property not found.</p>
  <a href="{{ url_for('public.home') }}" class="btn btn-jk-accent">Home</a>
</div>
{% endblock %}
""",
    "public/_listing_media.html": """{% macro render_listing_media(p, height=220, badge_text=None) %}
{% set image_paths = p.listing_images if p.listing_images is defined else [] %}
{% set video_paths = p.listing_videos if p.listing_videos is defined else [] %}

{% if not image_paths and not video_paths %}
<div class="listing-media listing-media--empty" style="--listing-media-height: {{ height }}px">
  <i class="bi bi-building"></i>
</div>
{% else %}
<div class="listing-media" style="--listing-media-height: {{ height }}px" data-default-tab="{{ 'photos' if image_paths else 'videos' }}">
  <div class="listing-media-badges">
    {% if image_paths %}<span class="listing-media-badge"><i class="bi bi-images"></i> {{ image_paths|length }}</span>{% endif %}
    {% if video_paths %}<span class="listing-media-badge listing-media-badge--video"><i class="bi bi-camera-video"></i> {{ video_paths|length }}</span>{% endif %}
    {% if badge_text %}<span class="jv-property-badge">{{ badge_text }}</span>{% endif %}
  </div>
  {% if image_paths and video_paths %}
  <div class="listing-media-tabs" role="tablist">
    <button type="button" class="listing-media-tab is-active" data-tab="photos" role="tab">Photos</button>
    <button type="button" class="listing-media-tab" data-tab="videos" role="tab">Videos</button>
  </div>
  {% endif %}
  <div class="listing-media-panel listing-media-panel--photos{% if not image_paths %} d-none{% endif %}">
    {% for path in image_paths %}
    <img src="{{ url_for('uploads', filename=path) }}" alt="" class="listing-media-slide{% if loop.first %} is-active{% endif %}" loading="lazy">
    {% endfor %}
    {% if image_paths|length > 1 %}
    <button type="button" class="listing-media-nav listing-media-prev" aria-label="Previous photo"><i class="bi bi-chevron-left"></i></button>
    <button type="button" class="listing-media-nav listing-media-next" aria-label="Next photo"><i class="bi bi-chevron-right"></i></button>
    <div class="listing-media-dots">
      {% for path in image_paths %}
      <button type="button" class="listing-media-dot{% if loop.first %} is-active{% endif %}" data-index="{{ loop.index0 }}" aria-label="Photo {{ loop.index }}"></button>
      {% endfor %}
    </div>
    {% endif %}
  </div>
  <div class="listing-media-panel listing-media-panel--videos{% if not video_paths %} d-none{% endif %}">
    {% for path in video_paths %}
    <div class="listing-media-video{% if loop.first %} is-active{% endif %}">
      <video controls playsinline preload="metadata" src="{{ url_for('uploads', filename=path) }}"></video>
    </div>
    {% endfor %}
  </div>
</div>
{% endif %}
{% endmacro %}
""",
    "public/_property_card.html": """{% from "public/_listing_media.html" import render_listing_media %}
<div class="col-12 col-md-6 col-lg-4">
  <div class="card property-card">
    {{ render_listing_media(p) }}
    <div class="card-body">
      <div class="d-flex flex-wrap gap-2 mb-2">
        <span class="badge badge-listed"><i class="bi bi-check-circle"></i> Listed</span>
        <span class="badge badge-type text-uppercase">{{ p.display_type or p.property_type }}</span>
        <span class="badge badge-status {% if p.listing_intent == 'rent' %}badge-rent bg-info{% else %}badge-buy bg-success{% endif %}">
          {{ 'For Rent' if p.listing_intent == 'rent' else 'For Sale' }}
        </span>
      </div>
      <h5 class="card-title mt-2">
        <a href="{{ url_for('public.property_detail', slug=p.slug) }}" class="text-decoration-none text-dark">
          {{ p.property_name }}
        </a>
      </h5>
      <p class="text-muted mb-1"><i class="bi bi-rulers"></i> {{ p.sq_ft|int }} sq.ft</p>
      <p class="text-muted mb-2"><i class="bi bi-geo-alt"></i> {{ p.area_name }}, Surat</p>
      <p class="price mb-2">₹{{ "{:,.0f}".format(p.price) }}{% if p.listing_type=='rent' %}/mo{% endif %}</p>
      <p class="small text-muted line-clamp-2">{{ p.description or 'Premium property listing with verified details and expert support.' }}</p>
      <div class="d-flex gap-2 mt-2 flex-wrap">
        <a href="{{ url_for('public.property_detail', slug=p.slug) }}" class="btn btn-sm btn-jk-primary">View Details</a>
        <a href="{{ url_for('public.property_detail', slug=p.slug) }}#visitPanel" class="btn btn-sm btn-jk-outline btn-request-visit">Request Site Visit</a>
        <a href="{{ url_for('public.property_detail', slug=p.slug) }}#inquiryPanel" class="btn btn-sm btn-jk-accent btn-send-inquiry">Send Inquiry</a>
      </div>
    </div>
  </div>
</div>
""",
    "public/about.html": """{% extends "public/base.html" %}
{% block title %}About Us - {{ company_name }}{% endblock %}
{% block content %}
<section class="about-hero jk-flow py-5">
  <div class="container">
    <article class="about-hero-card premium-hover-card reveal-on-scroll">
      <p class="about-kicker mb-2">About {{ company_name }}</p>
      <h1 class="about-hero-title">Trusted Property Guidance in Surat</h1>
      <p class="about-hero-text mb-0">
        {{ company_name }} helps buyers, sellers, and renters close clearer deals —
        with verified listings, transparent advice, and end-to-end support.
      </p>
    </article>
  </div>
</section>

<section class="container pb-5 jk-flow" id="leadership">
  <h2 class="section-title section-title-center mb-4">Leadership</h2>
  <div class="row g-4 leadership-row">
    <div class="col-12 col-md-6">
      <article class="leadership-card founder-card premium-hover-card reveal-on-scroll h-100">
        <img
          src="{{ url_for('static', filename='img/founder-photo.webp') }}"
          alt="Kalpesh Chunawala - Founder of JAKKASH Property Consultancy"
          class="founder-photo"
        >
        <p class="founder-label mb-1">Founder</p>
        <h3 class="founder-name">Kalpesh Chunawala</h3>
        <p class="founder-role mb-2">Founder · JAKKASH Property Consultancy</p>
        <blockquote class="about-quote-card mb-3">
          <p class="mb-0">"A property is not just a place to live; it is the foundation of dreams, security, and future generations."</p>
        </blockquote>
        <p class="mb-0 text-muted">
          Built JAKKASH into a client-first consultancy known for honest pricing and reliable site visits across Surat.
          His focus on verified inventory and clear communication has helped families close homes with confidence.
        </p>
      </article>
    </div>
    <div class="col-12 col-md-6">
      <article class="leadership-card founder-card premium-hover-card reveal-on-scroll h-100">
        <img
          src="{{ url_for('static', filename='img/company-logo-mark.webp') }}"
          alt="Co-Founder - JAKKASH Property Consultancy"
          class="founder-photo"
        >
        <p class="founder-label mb-1">Co-Founder</p>
        <h3 class="founder-name">JAKKASH Leadership</h3>
        <p class="founder-role mb-2">Co-Founder · Operations &amp; Client Success</p>
        <blockquote class="about-quote-card mb-3">
          <p class="mb-0">"Great brokerage is measured by trust delivered after the handshake."</p>
        </blockquote>
        <p class="mb-0 text-muted">
          Strengthens day-to-day operations, listing quality, and client follow-through so every inquiry moves with speed.
          Partners with the founder to keep rentals and sales pipelines transparent from first call to handover.
        </p>
      </article>
    </div>
  </div>
</section>

<section class="container pb-5 jk-flow">
  <div class="row g-4">
    <div class="col-12">
      <article class="about-info-card premium-hover-card reveal-on-scroll">
        <div class="about-info-icon"><i class="bi bi-buildings"></i></div>
        <div>
          <h3>About Company</h3>
          <p class="mb-0">
            JAKKASH Property Consultancy simplifies buying, selling, and renting across Surat with verified listings and professional guidance.
          </p>
        </div>
      </article>
    </div>
    <div class="col-md-6">
      <article class="about-info-card premium-hover-card reveal-on-scroll h-100">
        <div class="about-info-icon"><i class="bi bi-eye"></i></div>
        <div>
          <h3>Our Vision</h3>
          <p class="mb-0">To be Surat's most trusted, customer-focused property consultancy.</p>
        </div>
      </article>
    </div>
    <div class="col-md-6">
      <article class="about-info-card premium-hover-card reveal-on-scroll h-100">
        <div class="about-info-icon"><i class="bi bi-bullseye"></i></div>
        <div>
          <h3>Our Mission</h3>
          <p class="mb-0">Deliver transparent, reliable real-estate service that helps clients decide with confidence.</p>
        </div>
      </article>
    </div>
  </div>
</section>

<section class="about-stats-section py-5">
  <div class="container">
    <h2 class="section-title section-title-center">Our Growth in Numbers</h2>
    <div class="row g-4">
      <div class="col-6 col-lg-3">
        <article class="about-stat-card premium-hover-card reveal-on-scroll h-100">
          <p class="about-stat-value" data-counter="{{ about_stats.properties_listed }}" data-suffix="+">0</p>
          <p class="about-stat-label mb-0">Properties Listed</p>
        </article>
      </div>
      <div class="col-6 col-lg-3">
        <article class="about-stat-card premium-hover-card reveal-on-scroll h-100">
          <p class="about-stat-value" data-counter="{{ about_stats.happy_clients }}" data-suffix="+">0</p>
          <p class="about-stat-label mb-0">Happy Clients</p>
        </article>
      </div>
      <div class="col-6 col-lg-3">
        <article class="about-stat-card premium-hover-card reveal-on-scroll h-100">
          <p class="about-stat-value" data-counter="{{ about_stats.successful_deals }}" data-suffix="+">0</p>
          <p class="about-stat-label mb-0">Successful Deals</p>
        </article>
      </div>
      <div class="col-6 col-lg-3">
        <article class="about-stat-card premium-hover-card reveal-on-scroll h-100">
          <p class="about-stat-value" data-counter="{{ about_stats.years_experience }}" data-suffix="+">0</p>
          <p class="about-stat-label mb-0">Years Experience</p>
        </article>
      </div>
    </div>
  </div>
</section>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/about.js') }}"></script>
{% endblock %}
""",
    "public/ai_chatbot.html": """{% extends "public/base.html" %}
{% block title %}JAKKASH Property Assistant - {{ company_name }}{% endblock %}
{% block content %}
<section class="container py-5">
  <h1 class="section-title">JAKKASH Property Assistant</h1>
  <p class="text-muted">
    Menu-guided help for browsing listings, selling a property, contacting a broker, and FAQs.
  </p>
  <p><a class="btn btn-jk-accent" href="{{ url_for('public.chatbot') }}">Open Property Assistant</a></p>
</section>
{% endblock %}
""",
    "public/base.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="description" content="{{ company_name }} - Premium real estate consultancy in Surat for Buy, Sell and Rent properties.">
  <meta name="csrf-token" content="{{ csrf_token() }}">
  <title>{% block title %}{{ company_name }}{% endblock %}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Montserrat:wght@500;600;700;800&family=Playfair+Display:wght@500;600;700&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css" rel="stylesheet">
  <link href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jakkash.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/jovista-theme.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/responsive.css') }}" rel="stylesheet">
  <link href="{{ url_for('static', filename='css/mobile.css') }}" rel="stylesheet">
  {% block head_meta %}{% endblock %}
  {% block extra_css %}{% endblock %}
</head>
<body class="jk-jovista{% if request.endpoint == 'public.home' %} jk-home{% endif %}">
  <nav class="navbar navbar-expand-lg navbar-light jv-navbar sticky-top">
    <div class="container">
      <a class="navbar-brand d-flex align-items-center gap-2" href="{{ url_for('public.home') }}">
        <span class="jk-logo-badge">
          <img src="{{ url_for('static', filename='img/company-logo-mark.png') }}" alt="{{ company_name }}" class="jk-logo jk-logo-mark">
        </span>
      </a>

      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#publicNavbar" aria-controls="publicNavbar" aria-expanded="false" aria-label="Toggle navigation">
        <span class="navbar-toggler-icon"></span>
      </button>

      <div class="collapse navbar-collapse" id="publicNavbar">
        <ul class="navbar-nav public-main-nav mx-lg-auto mb-2 mb-lg-0 align-items-lg-center">
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'public.home' %}active{% endif %}" href="{{ url_for('public.home') }}">Home</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'public.listings' %}active{% endif %}" href="{{ url_for('public.listings') }}">Properties</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'public.services' %}active{% endif %}" href="{{ url_for('public.services') }}">Services</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'public.about' %}active{% endif %}" href="{{ url_for('public.about') }}">About Us</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'public.testimonials' %}active{% endif %}" href="{{ url_for('public.testimonials') }}">Testimonials</a></li>
          <li class="nav-item"><a class="nav-link {% if request.endpoint == 'public.contact' %}active{% endif %}" href="{{ url_for('public.contact') }}">Contact Us</a></li>
        </ul>

        <div class="d-flex flex-column flex-sm-row align-items-stretch align-items-lg-center gap-2 mt-3 mt-lg-0 ms-lg-auto header-actions">
          <a class="btn btn-jk-outline btn-sm header-action-btn" href="tel:{{ company_phone_raw }}">
            <i class="bi bi-telephone"></i> Call
          </a>
          <a class="btn btn-jk-accent btn-sm header-action-btn" href="{{ url_for('public.sell_property') }}">
            <i class="bi bi-plus-circle"></i> Sell Property
          </a>
        </div>
      </div>
    </div>
  </nav>

  {% with messages = get_flashed_messages(with_categories=true) %}
  {% if messages %}
  <div class="container mt-3">{% for cat, msg in messages %}<div class="alert alert-{{ cat }}">{{ msg }}</div>{% endfor %}</div>
  {% endif %}{% endwith %}

  <main class="page-enter">{% block content %}{% endblock %}</main>

  {% block page_overlays %}{% endblock %}

  <section class="contact-strip py-3">
    <div class="container d-flex flex-wrap align-items-center justify-content-between gap-3">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-telephone-fill"></i>
        <span>Speak to our property experts: <strong>{{ company_phone }}</strong></span>
      </div>
      <div class="d-flex gap-2">
        <a href="tel:{{ company_phone_raw }}" class="btn btn-jk-primary btn-sm"><i class="bi bi-telephone"></i> Call Now</a>
        <a href="https://wa.me/{{ company_whatsapp }}?text=Hello%20JAKKASH%20Property%20Consultancy.%20I%20need%20help%20with%20a%20property." target="_blank" class="btn btn-success btn-sm"><i class="bi bi-whatsapp"></i> WhatsApp</a>
      </div>
    </div>
  </section>

  <footer class="jk-footer jv-footer">
    <div class="container">
      <div class="row g-4 g-lg-5 jv-footer-main">
        <div class="col-md-6 col-lg-4">
          <span class="jk-logo-footer-wrap mb-3 d-inline-flex">
            <img src="{{ url_for('static', filename='img/company-logo-full.png') }}" alt="{{ company_name }}" class="jk-logo-footer">
          </span>
          <p class="jv-footer-tagline mb-2">
            Premium real estate consultancy for buy, sell, and rent opportunities across Surat.
          </p>
          <p class="jv-footer-brand mb-0">JAKKASH PROPERTY CONSULTANCY</p>
        </div>
        <div class="col-sm-6 col-lg-4">
          <h6 class="jv-footer-heading">Contact</h6>
          <ul class="jv-footer-list list-unstyled mb-0">
            <li><i class="bi bi-geo-alt" aria-hidden="true"></i> {{ company_address }}</li>
            <li><i class="bi bi-telephone" aria-hidden="true"></i> <a href="tel:{{ company_phone_raw }}">{{ company_phone }}</a></li>
            <li><i class="bi bi-envelope" aria-hidden="true"></i> <a href="mailto:{{ company_email }}">{{ company_email }}</a></li>
          </ul>
        </div>
        <div class="col-sm-6 col-lg-4">
          <h6 class="jv-footer-heading">Quick Links</h6>
          <ul class="jv-footer-links list-unstyled mb-0">
            <li><a href="{{ url_for('public.about') }}">About Us</a></li>
            <li><a href="{{ url_for('public.services') }}">Services</a></li>
            <li><a href="{{ url_for('public.listings') }}">Browse Properties</a></li>
            <li><a href="{{ url_for('public.chatbot') }}">Property Assistant</a></li>
            <li><a href="{{ url_for('public.property_map') }}">Surat Map</a></li>
            <li><a href="{{ url_for('public.sell_property') }}">Sell Your Property</a></li>
          </ul>
          <div class="jv-footer-social d-flex gap-2 mt-3">
            <a href="https://wa.me/{{ company_whatsapp }}" target="_blank" rel="noopener noreferrer" class="jv-footer-social-btn jv-footer-social-wa" aria-label="WhatsApp"><i class="bi bi-whatsapp" aria-hidden="true"></i></a>
            <a href="tel:{{ company_phone_raw }}" class="jv-footer-social-btn" aria-label="Call us"><i class="bi bi-telephone" aria-hidden="true"></i></a>
            <a href="mailto:{{ company_email }}" class="jv-footer-social-btn" aria-label="Email us"><i class="bi bi-envelope" aria-hidden="true"></i></a>
          </div>
        </div>
      </div>
      <div class="jv-footer-bottom">
        <p class="mb-0">&copy; 2026 {{ company_name }}. All rights reserved.</p>
      </div>
    </div>
  </footer>

  <div class="fab-stack" role="group" aria-label="Quick contact actions">
    <a href="{{ url_for('public.chatbot') }}" class="chatbot-float" aria-label="Open Property Assistant">
      <i class="bi bi-chat-dots-fill" aria-hidden="true"></i>
      <span class="visually-hidden">Property Assistant</span>
    </a>
    <a href="https://wa.me/{{ company_whatsapp }}?text=Hello%20JAKKASH%20Property%20Consultancy.%20I%20want%20property%20details." class="whatsapp-float" target="_blank" rel="noopener noreferrer" aria-label="WhatsApp us">
      <i class="bi bi-whatsapp" aria-hidden="true"></i>
    </a>
  </div>

  <button id="quickInquiryToggle" class="quick-inquiry-toggle" type="button">
    <i class="bi bi-chat-dots-fill"></i> Quick Inquiry
  </button>
  <aside id="quickInquiryPanel" class="quick-inquiry-panel" aria-hidden="true">
    <div class="quick-inquiry-header">
      <h6 class="mb-0">Quick Inquiry</h6>
      <button type="button" id="quickInquiryClose" class="btn btn-sm btn-light"><i class="bi bi-x-lg"></i></button>
    </div>
    <p class="small text-muted mb-3">Share your requirement and our team will contact you shortly.</p>
    <form id="quickInquiryForm" class="d-grid gap-2">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <input type="text" class="form-control" name="name" placeholder="Name *" required>
      <input type="text" class="form-control" name="mobile" placeholder="Mobile *" required>
      <input type="email" class="form-control" name="email" placeholder="Email">
      <textarea class="form-control" name="message" rows="3" placeholder="Property requirement"></textarea>
      <button class="btn btn-jk-accent" type="submit">Submit Inquiry</button>
    </form>
  </aside>

  <nav class="jk-mobile-nav d-lg-none" aria-label="Mobile quick navigation">
    <a href="{{ url_for('public.home') }}" class="jk-mobile-nav__item" data-nav="/">
      <i class="bi bi-house-door" aria-hidden="true"></i>
      <span>Home</span>
    </a>
    <a href="{{ url_for('public.listings') }}" class="jk-mobile-nav__item" data-nav="/properties">
      <i class="bi bi-buildings" aria-hidden="true"></i>
      <span>Properties</span>
    </a>
    <a href="{{ url_for('public.chatbot') }}" class="jk-mobile-nav__item jk-mobile-nav__item--accent" data-nav="/chatbot">
      <i class="bi bi-chat-dots-fill" aria-hidden="true"></i>
      <span>Help</span>
    </a>
    <a href="https://wa.me/{{ company_whatsapp }}?text=Hello%20JAKKASH%20Property%20Consultancy." class="jk-mobile-nav__item" target="_blank" rel="noopener noreferrer">
      <i class="bi bi-whatsapp" aria-hidden="true"></i>
      <span>WhatsApp</span>
    </a>
  </nav>

  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="{{ url_for('static', filename='js/app.js') }}"></script>
  <script src="{{ url_for('static', filename='js/animations.js') }}"></script>
  <script src="{{ url_for('static', filename='js/mobile.js') }}"></script>
  {% block extra_js %}{% endblock %}
</body>
</html>
""",
    "public/chatbot.html": """{% extends "public/base.html" %}
{% block title %}JAKKASH Property Assistant - {{ company_name }}{% endblock %}
{% block content %}
<section class="chatbot-page py-4 py-lg-5">
  <div class="container">
    <div class="row justify-content-center">
      <div class="col-xl-10 col-xxl-9">
        <header class="chatbot-page-header text-center mb-4 scroll-reveal">
          <span class="chatbot-kicker">Jakkash Property Consultancy</span>
          <h1 class="chatbot-page-title">JAKKASH Property Assistant</h1>
          <p class="chatbot-page-lead text-muted mb-0">
            Guided help for browsing listings, selling your property, contacting a broker, or reading FAQs. Tap an option to continue.
          </p>
        </header>

        <div
          class="chatbot-shell scroll-reveal"
          data-phone="{{ company_phone_raw }}"
          data-whatsapp="{{ company_whatsapp }}"
          data-address="{{ company_address }}"
        >
          <div class="chatbot-header">
            <div class="chatbot-header-avatar" aria-hidden="true">
              <i class="bi bi-building"></i>
            </div>
            <div class="chatbot-header-copy">
              <h2 class="chatbot-header-title mb-0">JAKKASH Property Assistant</h2>
              <p class="chatbot-header-status mb-0">
                <span class="chatbot-status-dot"></span> Online · Menu-guided Surat property help
              </p>
            </div>
          </div>

          <div id="chatMessages" class="chat-messages" role="log" aria-live="polite" aria-relevant="additions">
            <div class="chat-msg assistant chat-msg--visible">
              <span class="chat-avatar chat-avatar--bot" aria-hidden="true"><i class="bi bi-building"></i></span>
              <div class="bubble">
                Welcome to <strong>JAKKASH Property Consultancy</strong>.<br><br>
                Use the quick-select buttons below to browse properties, list a property for sale, speak with a broker, or read FAQs.
              </div>
            </div>
          </div>

          <form id="chatForm" class="chat-form">
            <div class="chat-input-wrap">
              <input
                id="chatInput"
                type="text"
                class="form-control chat-input"
                placeholder="Optional: type hello, contact, or address…"
                autocomplete="off"
                aria-label="Optional short keyword"
              >
            </div>
            <button id="chatSendBtn" class="btn btn-jk-accent chat-send-btn" type="submit" aria-label="Send keyword">
              <span class="chat-send-label">Send</span>
              <i class="bi bi-send-fill chat-send-icon" aria-hidden="true"></i>
            </button>
          </form>

          <div class="chat-suggestions">
            <span class="chat-suggestions-label">Quick select</span>
            <div id="chatMenu" class="chat-suggestions-list" role="group" aria-label="Assistant options">
              <button type="button" class="chat-chip" data-action="browse">Browse Properties</button>
              <button type="button" class="chat-chip" data-action="sell">Sell My Property</button>
              <button type="button" class="chat-chip" data-action="broker">Speak to a Broker</button>
              <button type="button" class="chat-chip" data-action="faq">Frequently Asked Questions</button>
            </div>
          </div>

          <div id="chatPropertyResults" class="chat-property-results row g-4"></div>
        </div>
      </div>
    </div>
  </div>
</section>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/chatbot.js') }}"></script>
{% endblock %}
""",
    "public/compare.html": """{% extends "public/base.html" %}
{% block title %}Compare Properties{% endblock %}
{% block content %}
<div class="container py-5 jk-flow">
  <h1 class="section-title">Compare Properties</h1>
  <p class="text-muted">Save properties from listings, then compare them here.</p>
  <div id="compareTable" class="table-responsive"></div>
</div>
{% endblock %}
{% block extra_js %}
<script>
(async () => {
  const r = await fetch('/api/saved');
  const d = await r.json();
  const el = document.getElementById('compareTable');
  if (!d.properties?.length) { el.innerHTML = '<p>No saved properties. <a href="/properties">Browse listings</a></p>'; return; }
  const props = d.properties.slice(0, 4);
  const rows = [['Name',...props.map(p=>p.property_name)],['Area',...props.map(p=>p.area_name)],['Price',...props.map(p=>'₹'+p.price.toLocaleString('en-IN')]],['BHK',...props.map(p=>p.bhk)],['Sq Ft',...props.map(p=>p.sq_ft)],['Type',...props.map(p=>p.property_type)]];
  el.innerHTML = '<table class="table table-bordered"><tbody>'+rows.map(r=>'<tr>'+r.map((c,i)=>'<'+(i?'td':'th')+'>'+c+'</'+(i?'td':'th')+'>').join('')+'</tr>').join('')+'</tbody></table>';
})();
</script>
{% endblock %}
""",
    "public/contact.html": """{% extends "public/base.html" %}
{% block title %}{% if intent == 'visit' %}Request Site Visit{% else %}Contact{% endif %} - {{ company_name }}{% endblock %}
{% block content %}
<div class="container py-5 jk-flow">
  <div class="row g-5">
    <div class="col-lg-6 reveal-on-scroll">
      <h1 class="section-title">{% if intent == 'visit' %}Request Site Visit{% else %}Contact Us{% endif %}</h1>
      <p class="mb-1"><strong>{{ company_name }}</strong></p>
      <p class="mb-1"><i class="bi bi-geo-alt text-warning"></i> {{ company_address }}</p>
      <p class="mb-1"><i class="bi bi-telephone"></i> Mobile: <a href="tel:{{ company_phone_raw }}">{{ company_phone }}</a></p>
      <p class="mb-1"><i class="bi bi-whatsapp text-success"></i> WhatsApp: <a href="https://wa.me/{{ company_whatsapp }}" target="_blank">{{ company_phone }}</a></p>
      <p class="mb-3"><i class="bi bi-envelope"></i> Email: <a href="mailto:{{ company_email }}">{{ company_email }}</a></p>

      {% if linked_property %}
      <div class="alert alert-light border mb-3">
        <div class="fw-semibold">{{ linked_property.property_name }}</div>
        <div class="small text-muted">{{ linked_property.area_name }}, Surat · {{ 'For Rent' if linked_property.listing_intent == 'rent' else 'For Sale' }}</div>
      </div>
      {% endif %}

      <form id="contactForm" class="mt-4 content-card">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        {% if linked_property %}<input type="hidden" name="property_id" value="{{ linked_property.id }}">{% endif %}
        <input type="hidden" name="source" value="{{ 'site_visit_request' if intent == 'visit' else 'contact_form' }}">
        <div class="mb-3"><input class="form-control" name="name" id="contactNameInput" placeholder="Name *" required autofocus></div>
        <div class="mb-3"><input class="form-control" name="mobile" placeholder="Mobile *" required></div>
        <div class="mb-3"><input class="form-control" name="email" type="email" placeholder="Email *" required></div>
        <div class="mb-3">
          <textarea class="form-control" name="message" rows="4" placeholder="{% if intent == 'visit' %}Preferred visit date / time and notes{% else %}Your message{% endif %}">{% if linked_property and intent == 'visit' %}I would like to schedule a site visit for {{ linked_property.property_name }}.{% elif linked_property %}Inquiry about {{ linked_property.property_name }}.{% endif %}</textarea>
        </div>
        <button class="btn btn-jk-accent">{% if intent == 'visit' %}Submit Visit Request{% else %}Send Message{% endif %}</button>
      </form>
    </div>
    <div class="col-lg-6 reveal-on-scroll">
      <div class="ratio ratio-4x3 rounded overflow-hidden shadow-sm content-card p-0">
        <iframe
          src="https://www.google.com/maps?q={{ (company_address if company_address else (company_lat ~ ',' ~ company_lng))|replace(' ', '+') }}&output=embed"
          loading="lazy"
          referrerpolicy="no-referrer-when-downgrade"></iframe>
      </div>
    </div>
  </div>
</div>
{% endblock %}
{% block extra_js %}
<script>
document.getElementById('contactForm')?.addEventListener('submit', async e => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const body = Object.fromEntries(fd);
  if (!body.source) body.source = 'contact_form';
  const r = await apiFetch('/api/inquiry', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const d = await r.json();
  alert(d.message || d.error);
  if(d.success) e.target.reset();
});
document.getElementById('contactNameInput')?.focus();
</script>
{% endblock %}
""",
    "public/detail.html": """{% extends "public/base.html" %}
{% block title %}{{ property.property_name }} - {{ company_name }}{% endblock %}
{% block head_meta %}
{% set cover = None %}
{% if media.images and media.images|length %}
  {% set cover = url_for('uploads', filename=media.images[0].file_path, _external=True) %}
{% elif property.primary_image %}
  {% set cover = url_for('uploads', filename=property.primary_image, _external=True) %}
{% endif %}
<meta property="og:type" content="website">
<meta property="og:title" content="{{ property.property_name }} | {{ company_name }}">
<meta property="og:description" content="{{ (property.description or (property.property_name ~ ' in ' ~ (property.area_name or 'Surat')))|truncate(160, True) }}">
<meta property="og:url" content="{{ request.url }}">
{% if cover %}<meta property="og:image" content="{{ cover }}">{% endif %}
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{{ property.property_name }} | {{ company_name }}">
{% if cover %}<meta name="twitter:image" content="{{ cover }}">{% endif %}
{% endblock %}
{% block content %}
<div class="container py-5 detail-page jk-flow" data-property-id="{{ property.id }}" data-property-area="{{ property.area_name }}, Surat">
  <div class="row g-4">
    <div class="col-lg-7 reveal-on-scroll">
      {% set imgs = media.images %}
      {% if imgs %}
      <img id="mainImg" class="gallery-main mb-2" src="{{ url_for('uploads', filename=imgs[0].file_path) }}" alt="">
      <div class="d-flex gap-2 flex-wrap">
        {% for img in imgs %}
        <img class="gallery-thumb {% if loop.first %}active{% endif %}" src="{{ url_for('uploads', filename=img.file_path) }}" data-full="{{ url_for('uploads', filename=img.file_path) }}">
        {% endfor %}
      </div>
      {% elif property.primary_image %}
      <img class="gallery-main" src="{{ url_for('uploads', filename=property.primary_image) }}" alt="">
      {% else %}
      <div class="gallery-main bg-secondary d-flex align-items-center justify-content-center"><i class="bi bi-building text-white display-1"></i></div>
      {% endif %}

      {% if media.videos %}
      <h5 class="mt-4">Videos</h5>
      {% for v in media.videos %}
      <video class="w-100 rounded mb-2" controls src="{{ url_for('uploads', filename=v.file_path) }}"></video>
      {% endfor %}
      {% endif %}
    </div>
    <div class="col-lg-5 reveal-on-scroll">
      <div class="d-flex flex-wrap gap-2 mb-2">
        <span class="badge badge-type">{{ property.display_type or property.property_type }}</span>
        <span class="badge badge-status {% if property.listing_intent == 'rent' %}badge-rent bg-info{% else %}badge-buy bg-success{% endif %}">
          {{ 'For Rent' if property.listing_intent == 'rent' else 'For Sale' }}
        </span>
      </div>
      <h1 class="h3 mt-2">{{ property.property_name }}</h1>
      <p class="text-muted mb-2"><i class="bi bi-geo-alt"></i> {{ property.area_name }}, Surat</p>
      <p class="price fs-3 fw-bold">₹{{ "{:,.0f}".format(property.price) }}{% if property.listing_type == 'rent' %}/mo{% endif %}</p>
      <ul class="list-unstyled detail-meta-list">
        <li><strong>Property ID:</strong> #{{ property.id }}</li>
        <li><strong>Property Name:</strong> {{ property.property_name }}</li>
        <li><strong>Property Type:</strong> {{ property.display_type or property.property_type }}</li>
        <li><strong>Listing Intent:</strong> {{ 'For Rent' if property.listing_intent == 'rent' else 'For Sale' }}</li>
        {% if property.bhk %}<li><strong>BHK:</strong> {{ property.bhk }}</li>{% endif %}
        <li><strong>Area:</strong> {{ property.sq_ft|int }} sq.ft</li>
        <li><strong>Locality:</strong> {{ property.area_name }}, Surat</li>
      </ul>
      {% if property.amenities %}
      <div class="mb-3">
        <h6 class="mb-2">Amenities</h6>
        {% for a in property.amenities %}
        <span class="badge bg-light text-dark border me-1 mb-1">{{ a }}</span>
        {% endfor %}
      </div>
      {% endif %}
      <p>{{ property.description or "Property description will be shared by our team on inquiry." }}</p>
      <div class="d-grid gap-2">
        <a href="{{ wa_link }}" target="_blank" class="btn btn-success btn-whatsapp" data-wa="{{ wa_link }}">
          <i class="bi bi-whatsapp"></i> WhatsApp Broker
        </a>
        <a href="tel:{{ company_phone_raw }}" class="btn btn-jk-primary btn-call"><i class="bi bi-telephone"></i> Call Broker</a>
        <a class="btn btn-jk-accent btn-send-inquiry" href="#inquiryPanel">
          <i class="bi bi-send"></i> Send Inquiry
        </a>
        <a class="btn btn-jk-outline btn-request-visit" href="#visitPanel">
          <i class="bi bi-calendar-check"></i> Request Site Visit
        </a>
        <button class="btn btn-outline-secondary btn-share" type="button" data-action="share-property"><i class="bi bi-share"></i> Share Property</button>
      </div>
      {% if media.documents %}
      <h6 class="mt-4">Documents</h6>
      {% for d in media.documents %}
      <a href="{{ url_for('uploads', filename=d.file_path) }}" target="_blank" class="d-block"><i class="bi bi-file-pdf"></i> {{ d.doc_name }}</a>
      {% endfor %}
      {% endif %}
    </div>
  </div>

  <section class="mt-5 collapse show" id="inquiryPanel">
    <h3 class="section-title">Send Inquiry</h3>
    <form id="inquiryForm" class="row g-3">
      <input type="hidden" name="property_id" value="{{ property.id }}">
      <input type="hidden" name="intent" id="inquiryIntent" value="inquiry">
      <div class="col-md-6"><input class="form-control" name="name" id="inquiryNameInput" placeholder="Your Name" required></div>
      <div class="col-md-6"><input class="form-control" name="mobile" placeholder="Mobile" required></div>
      <div class="col-12"><input class="form-control" name="email" placeholder="Email"></div>
      <div class="col-12"><textarea class="form-control" name="message" rows="3" placeholder="Message"></textarea></div>
      <div class="col-12"><button class="btn btn-jk-accent">Submit Inquiry</button></div>
    </form>
  </section>

  <section class="mt-4 collapse" id="visitPanel">
    <h3 class="section-title">Request Site Visit</h3>
    <form id="visitForm" class="row g-3">
      <input type="hidden" name="property_id" value="{{ property.id }}">
      <input type="hidden" name="intent" value="site_visit">
      <div class="col-md-6"><input class="form-control" name="name" id="visitNameInput" placeholder="Your Name" required></div>
      <div class="col-md-6"><input class="form-control" name="mobile" placeholder="Mobile" required></div>
      <div class="col-md-6"><input class="form-control" name="email" placeholder="Email"></div>
      <div class="col-md-6"><input type="date" class="form-control" name="preferred_date" required></div>
      <div class="col-12"><textarea class="form-control" name="message" rows="3" placeholder="Preferred timing / notes"></textarea></div>
      <div class="col-12"><button class="btn btn-jk-primary">Request Site Visit</button></div>
    </form>
  </section>

  {% if similar %}
  <section class="mt-5">
    <h3 class="section-title">You May Also Like</h3>
    <div class="row g-4">{% for p in similar %}{% include "public/_property_card.html" %}{% endfor %}</div>
  </section>
  {% endif %}
</div>

<div class="modal fade" id="shareFallbackModal" tabindex="-1" aria-labelledby="shareFallbackTitle" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h5 class="modal-title" id="shareFallbackTitle">Share Property</h5>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">
        <img id="shareFallbackImage" src="" alt="" class="img-fluid rounded mb-3 d-none" style="max-height:180px;object-fit:cover;width:100%;">
        <p class="fw-semibold mb-1" id="shareFallbackName"></p>
        <input type="text" class="form-control" id="shareFallbackUrl" readonly>
      </div>
      <div class="modal-footer">
        <button type="button" class="btn btn-jk-accent" id="shareFallbackCopy">Copy Link</button>
      </div>
    </div>
  </div>
</div>
{% endblock %}
{% block extra_js %}<script src="{{ url_for('static', filename='js/detail.js') }}"></script>{% endblock %}
""",
    "public/home.html": """{% extends "public/base.html" %}
{% from "public/_listing_media.html" import render_listing_media %}
{% block title %}{{ company_name }} - Premium Properties in Surat{% endblock %}
{% block extra_css %}
<link href="{{ url_for('static', filename='css/property-hero.css') }}" rel="stylesheet">
{% endblock %}
{% block content %}
<section class="property-hero" id="propertyHero" aria-label="Property showcase hero">

  <div class="property-hero__mode-toggle" role="tablist" aria-label="View mode">
    <button class="property-hero__mode-btn is-active" data-mode="split" role="tab" aria-selected="true">Split View</button>
    <button class="property-hero__mode-btn" data-mode="cinema" role="tab" aria-selected="false">Cinema</button>
  </div>

  <div class="property-hero__grid">

    <div class="property-hero__panel property-hero__panel--exterior is-visible">
      <div class="property-hero__video-wrap">
        <video class="property-hero__video" autoplay muted loop playsinline preload="auto">
          <source src="{{ url_for('static', filename='videos/hero-exterior.mp4') }}" type="video/mp4">
        </video>
      </div>
      <div class="property-hero__shade"></div>
    </div>

    <div class="property-hero__panel property-hero__panel--interior is-visible">
      <div class="property-hero__video-wrap">
        <video class="property-hero__video" autoplay muted loop playsinline preload="auto">
          <source src="{{ url_for('static', filename='videos/hero-interior.mp4') }}" type="video/mp4">
        </video>
      </div>
      <div class="property-hero__shade"></div>
    </div>

  </div>

  <div class="property-hero__divider" aria-hidden="true"></div>

  <div class="property-hero__content">
    <h1>Find Your Dream Home in Surat</h1>
    <div class="property-hero__actions">
      <a href="{{ url_for('public.listings') }}" class="property-hero__btn property-hero__btn--primary">View Listings</a>
      <a href="{{ url_for('public.sell_property') }}" class="property-hero__btn property-hero__btn--secondary">Sell your property</a>
    </div>
  </div>

</section>

<section class="jv-section jv-services">
  <div class="container">
    <div class="row g-4">
      <div class="col-12 col-md-4 scroll-reveal">
        <article class="jv-service-card">
          <div class="jv-service-icon"><i class="bi bi-house-heart"></i></div>
          <h2 class="jv-service-title">Residential Properties</h2>
          <p class="jv-service-text">Helping families find their perfect homes — from affordable flats to premium apartments and villas, matched to your lifestyle and budget.</p>
          <a href="{{ url_for('public.listings') }}?listing_intent=buy" class="jv-link">Explore residential</a>
        </article>
      </div>
      <div class="col-12 col-md-4 scroll-reveal">
        <article class="jv-service-card">
          <div class="jv-service-icon"><i class="bi bi-building"></i></div>
          <h2 class="jv-service-title">Commercial Properties</h2>
          <p class="jv-service-text">Shops, offices, showrooms, and retail spaces at strategic Surat locations for visibility, footfall, and long-term growth.</p>
          <a href="{{ url_for('public.listings') }}?type=commercial" class="jv-link">Explore commercial</a>
        </article>
      </div>
      <div class="col-12 col-md-4 scroll-reveal">
        <article class="jv-service-card">
          <div class="jv-service-icon"><i class="bi bi-key"></i></div>
          <h2 class="jv-service-title">Rent &amp; Investment</h2>
          <p class="jv-service-text">Rent-ready homes and investment-grade listings with verified details, site visits, and end-to-end advisory support.</p>
          <a href="{{ url_for('public.listings') }}?listing_intent=rent" class="jv-link">Explore rentals</a>
        </article>
      </div>
    </div>
  </div>
</section>

<section class="jv-section jv-stats-band">
  <div class="container">
    <div class="row g-4 text-center">
      <div class="col-12 col-md-4 scroll-reveal">
        <div class="jv-stat">
          <span class="jv-stat-value" data-counter="{{ home_stats.properties }}">{{ home_stats.properties }}</span>
          <span class="jv-stat-label">Properties Listed</span>
        </div>
      </div>
      <div class="col-12 col-md-4 scroll-reveal">
        <div class="jv-stat">
          <span class="jv-stat-value" data-counter="{{ home_stats.clients }}">{{ home_stats.clients }}</span>
          <span class="jv-stat-label">Clients Served</span>
        </div>
      </div>
      <div class="col-12 col-md-4 scroll-reveal">
        <div class="jv-stat">
          <span class="jv-stat-value" data-counter="{{ home_stats.years }}">{{ home_stats.years }}</span><span class="jv-stat-suffix">+</span>
          <span class="jv-stat-label">Years of Experience</span>
        </div>
      </div>
    </div>
  </div>
</section>

<section class="jv-section" id="about">
  <div class="container">
    <div class="jv-about-split scroll-reveal mb-5">
      <div class="jv-about-heading">
        <p class="jv-eyebrow jv-eyebrow--dark">About</p>
        <h2 class="jv-section-title">A modern living space with trusted guidance.</h2>
      </div>
      <div class="jv-about-body">
        <p class="jv-body-text">
          {{ company_name }} delivers transparent, customer-focused real estate services across Surat —
          whether you are buying, selling, or renting residential and commercial property.
        </p>
        <a href="{{ url_for('public.about') }}" class="btn btn-jk-accent mt-2">Learn more</a>
      </div>
    </div>
    <h3 class="section-title section-title-center mb-4 scroll-reveal">Leadership</h3>
    <div class="row g-4 leadership-row">
      <div class="col-12 col-md-6">
        <article class="leadership-card founder-card premium-hover-card reveal-on-scroll h-100">
          <img src="{{ url_for('static', filename='img/founder-photo.webp') }}" alt="Founder Kalpesh Chunawala" class="founder-photo">
          <p class="founder-label mb-1">Founder</p>
          <h4 class="founder-name">Kalpesh Chunawala</h4>
          <blockquote class="about-quote-card mb-3"><p class="mb-0">"A property is the foundation of dreams, security, and future generations."</p></blockquote>
          <p class="mb-0 text-muted">Built JAKKASH on verified listings and honest advice. Helps Surat families close homes with clarity and speed.</p>
        </article>
      </div>
      <div class="col-12 col-md-6">
        <article class="leadership-card founder-card premium-hover-card reveal-on-scroll h-100">
          <img src="{{ url_for('static', filename='img/company-logo-mark.webp') }}" alt="Co-Founder" class="founder-photo">
          <p class="founder-label mb-1">Co-Founder</p>
          <h4 class="founder-name">JAKKASH Leadership</h4>
          <blockquote class="about-quote-card mb-3"><p class="mb-0">"Great brokerage is measured by trust delivered after the handshake."</p></blockquote>
          <p class="mb-0 text-muted">Drives client success and listing quality so rentals and sales move smoothly from inquiry to handover.</p>
        </article>
      </div>
    </div>
  </div>
</section>

<section class="jv-section jv-section--muted">
  <div class="container">
    <div class="text-center mb-4 scroll-reveal">
      <p class="jv-eyebrow jv-eyebrow--dark">Discover</p>
      <h2 class="jv-section-title">Discover JAKKASH Spaces</h2>
      <p class="jv-body-text mx-auto" style="max-width:640px">
        Curated residential and commercial listings across Surat's most promising neighbourhoods.
      </p>
      <div class="d-flex flex-wrap justify-content-center gap-2 mt-3">
        <a href="{{ url_for('public.listings') }}" class="btn btn-jk-accent"><i class="bi bi-grid"></i> View All Listings</a>
        <a href="{{ url_for('public.listings') }}?listing_intent=buy" class="btn btn-jk-outline">For Sale</a>
        <a href="{{ url_for('public.listings') }}?listing_intent=rent" class="btn btn-jk-outline">For Rent</a>
      </div>
    </div>
    <div id="jvDiscoverGrid" class="row g-4 jv-discover-grid">
      {% for p in featured_properties %}
      <div class="col-12 col-md-6 col-lg-4">
        <article class="jv-property-card property-card">
          {{ render_listing_media(p, height=240, badge_text='For ' ~ ('Rent' if p.listing_intent == 'rent' else 'Sale')) }}
          <div class="jv-property-body">
            <h3 class="jv-property-title">
              <a href="{{ url_for('public.property_detail', slug=p.slug) }}">{{ p.property_name }}</a>
            </h3>
            <p class="jv-property-meta">{{ p.display_type or p.property_type }} · {{ p.area_name }}, Surat</p>
            <p class="jv-property-price">From ₹{{ "{:,.0f}".format(p.price) }}{% if p.listing_type == 'rent' %}/mo{% endif %}</p>
            <a href="{{ url_for('public.property_detail', slug=p.slug) }}" class="btn btn-sm btn-jk-primary">View Details</a>
          </div>
        </article>
      </div>
      {% else %}
      <div class="col-12 text-center text-muted py-2" id="jvDiscoverLoading">Loading properties…</div>
      {% endfor %}
    </div>
    <div class="text-center mt-4 scroll-reveal">
      <a href="{{ url_for('public.listings') }}" class="btn btn-jk-outline">View all properties</a>
    </div>
  </div>
</section>

<section class="jv-section">
  <div class="container">
    <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3 scroll-reveal">
      <h2 class="jv-section-title mb-0">Testimonials &amp; Reviews</h2>
      <a href="{{ url_for('public.testimonials') }}" class="btn btn-jk-outline btn-sm">View all</a>
    </div>
    <div class="row g-4 scroll-reveal-stagger">
      {% for t in testimonials %}
      <div class="col-12 col-md-6 col-lg-4">
        <article class="testimonial-card jv-testimonial h-100">
          <div class="text-warning mb-2">{% for _ in range(t.rating) %}<i class="bi bi-star-fill"></i>{% endfor %}</div>
          <p class="mb-3">"{{ t.review_text }}"</p>
          <strong>{{ t.client_name }}</strong><br><small class="text-muted">{{ t.client_location }}</small>
        </article>
      </div>
      {% else %}
      <p class="text-muted">No reviews yet. Be the first to share your experience.</p>
      {% endfor %}
    </div>
  </div>
</section>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/property-hero.js') }}"></script>
<script src="{{ url_for('static', filename='js/listing-media.js') }}"></script>
<script src="{{ url_for('static', filename='js/home.js') }}"></script>
<script>document.addEventListener('DOMContentLoaded', () => initListingMedia(document.getElementById('jvDiscoverGrid')));</script>
{% endblock %}
""",
    "public/listings.html": """{% extends "public/base.html" %}
{% block title %}Properties - {{ company_name }}{% endblock %}
{% block content %}
<div class="container py-5 listings-page">
  <div class="d-flex justify-content-between align-items-start align-items-md-center gap-3 mb-3 scroll-reveal">
    <div>
      <h1 class="section-title mb-1">Properties Listing</h1>
      <p class="text-muted mb-0">Browse approved properties with advanced filters and quick indexing search.</p>
    </div>
    <button type="button" id="openFilters" class="btn btn-outline-dark listings-filter-toggle">
      <i class="bi bi-list"></i> Filters
    </button>
  </div>

  <div class="listing-quick-nav mb-4">
    <p class="listing-quick-nav__label mb-2"><i class="bi bi-buildings"></i> Browse listings</p>
    <div class="listing-quick-nav__chips">
      <button type="button" class="listing-quick-chip is-active" data-quick-filter="">All Properties</button>
      <button type="button" class="listing-quick-chip" data-quick-filter="buy">For Buy</button>
      <button type="button" class="listing-quick-chip" data-quick-filter="rent">For Rent</button>
      <button type="button" class="listing-quick-chip" data-quick-type="apartment">Apartments</button>
      <button type="button" class="listing-quick-chip" data-quick-type="plot">Plots</button>
      <button type="button" class="listing-quick-chip" data-quick-type="commercial">Commercial</button>
    </div>
  </div>

  <div id="listingsPromo" class="listings-promo d-none" role="status" aria-live="polite">
    <div>
      <strong id="listingsPromoCount">0 properties</strong>
      <span class="text-muted"> available — tap <strong>View Details</strong> on any card to see full info.</span>
    </div>
    <a href="{{ url_for('public.sell_property') }}" class="btn btn-sm btn-jk-outline">List your property</a>
  </div>

  <div class="d-flex justify-content-between align-items-center mb-3 listings-toolbar">
    <strong id="resultsCount">Loading properties...</strong>
    <div class="btn-group" role="group">
      <button type="button" class="btn btn-outline-secondary active" id="viewGrid"><i class="bi bi-grid"></i></button>
      <button type="button" class="btn btn-outline-secondary" id="viewList"><i class="bi bi-list"></i></button>
    </div>
  </div>
  <div id="results" class="row g-4"></div>
  <div id="noResults" class="listings-empty d-none text-center py-5">
    <i class="bi bi-search listings-empty__icon" aria-hidden="true"></i>
    <h3 class="h5 mb-2">No properties match your filters</h3>
    <p class="text-muted mb-3">Try a different filter or browse all available listings.</p>
    <div class="d-flex flex-wrap justify-content-center gap-2">
      <button type="button" class="btn btn-jk-accent" id="browseAllBtn">View All Listings</button>
      <button type="button" class="btn btn-jk-outline" id="openFiltersFromEmpty">Open Filters</button>
    </div>
  </div>
</div>
{% endblock %}
{% block page_overlays %}
<div id="filterOverlay" class="filter-overlay" aria-hidden="true"></div>
<aside id="filterDrawer" class="filter-drawer" aria-hidden="true">
  <div class="filter-drawer-header">
    <h5 class="mb-0">Filters</h5>
    <button type="button" id="closeFilters" class="btn btn-sm btn-light" aria-label="Close filters">
      <i class="bi bi-x-lg"></i>
    </button>
  </div>

  <form id="filterForm" class="filter-drawer-form">
    <div class="filter-fields">
      <div class="filter-field">
        <label class="form-label">Search</label>
        <input class="form-control" name="q" id="f_q" placeholder="Name, locality, location">
      </div>

      <div class="filter-field">
        <label class="form-label">Property ID</label>
        <input class="form-control" name="property_id" id="f_property_id" placeholder="e.g. 102">
      </div>

      <div class="filter-field">
        <label class="form-label d-block mb-2">Status</label>
        <div class="btn-group w-100" role="group">
          <button type="button" class="btn btn-outline-secondary btn-intent active" data-intent="">All</button>
          <button type="button" class="btn btn-outline-secondary btn-intent" data-intent="buy">Buy</button>
          <button type="button" class="btn btn-outline-secondary btn-intent" data-intent="rent">Rent</button>
        </div>
        <input type="hidden" name="listing_intent" id="f_listing_intent">
      </div>

      <div class="filter-field">
        <label class="form-label">City / Area</label>
        <select class="form-select" name="area" id="f_area">
          <option value="">All Cities/Areas</option>
          {% for a in areas %}<option value="{{ a }}">{{ a }}</option>{% endfor %}
        </select>
      </div>

      <div class="filter-field">
        <label class="form-label">Property Type</label>
        <select class="form-select" name="type" id="f_type">
          <option value="">All Types</option>
          <option value="apartment">Apartment</option>
          <option value="flat">Flat</option>
          <option value="villa">Villa</option>
          <option value="bungalow">Bungalow</option>
          <option value="plot">Plot</option>
          <option value="commercial">Commercial</option>
          <option value="residential">Residential</option>
        </select>
      </div>

      <div class="filter-field">
        <label class="form-label">BHK</label>
        <select class="form-select" name="bhk" id="f_bhk">
          <option value="">Any</option>
          <option value="1">1</option>
          <option value="2">2</option>
          <option value="3">3</option>
          <option value="4">4+</option>
        </select>
      </div>

      <div class="filter-field">
        <label class="form-label">Minimum Sq Ft</label>
        <input type="number" class="form-control" name="min_sq_ft" id="f_min_sqft" placeholder="Min">
      </div>

      <div class="filter-field">
        <label class="form-label">Maximum Sq Ft</label>
        <input type="number" class="form-control" name="max_sq_ft" id="f_max_sqft" placeholder="Max">
      </div>

      <div class="filter-field">
        <label class="form-label">Minimum Budget</label>
        <input type="number" class="form-control" name="min_price" id="f_min" placeholder="Min ₹">
      </div>

      <div class="filter-field">
        <label class="form-label">Maximum Budget</label>
        <input type="number" class="form-control" name="max_price" id="f_max" placeholder="Max ₹">
      </div>

      <div class="filter-field">
        <label class="form-label">City</label>
        <input class="form-control" name="city" id="f_city" value="Surat">
      </div>

      <div class="filter-field">
        <label class="form-label">Locality</label>
        <input class="form-control" name="location" id="f_location" placeholder="Adajan, Vesu...">
      </div>

      <div class="filter-field">
        <label class="form-label">Sort By</label>
        <select class="form-select" name="sort" id="f_sort">
          <option value="newest">Newest</option>
          <option value="price_asc">Price Low-High</option>
          <option value="price_desc">Price High-Low</option>
          <option value="views">Most Viewed</option>
        </select>
      </div>
    </div>

    <div class="filter-actions">
      <button type="submit" class="btn btn-jk-accent">Apply Filters</button>
      <button type="button" id="resetFilters" class="btn btn-outline-secondary">Reset Filters</button>
    </div>
  </form>
</aside>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/listing-media.js') }}"></script>
<script src="{{ url_for('static', filename='js/listings.js') }}"></script>
{% endblock %}
""",
    "public/map.html": """{% extends "public/base.html" %}
{% block title %}Surat Property Map - {{ company_name }}{% endblock %}
{% block content %}
<div class="container py-5">
  <h1 class="section-title">Property Map View</h1>
  <p class="text-muted">Explore approved listings by approximate locality. Orange circles show general areas across Surat — exact building locations are not shown publicly.</p>
  <div class="map-legend mb-3 small">
    <span><span style="background:#e67e22"></span> Approximate Locality</span>
  </div>
  <div id="propertyMap"></div>
</div>
{% endblock %}
{% block extra_js %}<script src="{{ url_for('static', filename='js/map.js') }}"></script>{% endblock %}
""",
    "public/price_ai.html": """{% extends "public/base.html" %}
{% block title %}Price AI - {{ company_name }}{% endblock %}
{% block content %}
<section class="container py-5 jk-flow">
  <div class="row justify-content-center g-4">
    <div class="col-lg-7">
      <h1 class="section-title mb-2">Price AI Estimator</h1>
      <p class="text-muted mb-4">Estimate approximate market value from area, configuration, and size.</p>

      <div class="card shadow-sm border-0">
        <div class="card-body p-4">
          <form method="POST" class="row g-3">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div class="col-md-6">
              <label class="form-label">Area</label>
              <input class="form-control" name="area_name" value="{{ request.form.area_name or 'Vesu' }}" required>
            </div>
            <div class="col-md-3">
              <label class="form-label">BHK</label>
              <input type="number" class="form-control" name="bhk" value="{{ request.form.bhk or 2 }}" min="0">
            </div>
            <div class="col-md-3">
              <label class="form-label">Sq Ft</label>
              <input type="number" class="form-control" name="sq_ft" value="{{ request.form.sq_ft or 1200 }}" min="100" required>
            </div>
            <div class="col-md-6">
              <label class="form-label">Property Type</label>
              <select class="form-select" name="property_type">
                {% for t in types %}
                <option value="{{ t }}" {% if request.form.property_type == t %}selected{% endif %}>{{ t|replace('_', ' ')|title }}</option>
                {% endfor %}
              </select>
            </div>
            <div class="col-md-6 d-flex align-items-end">
              <button class="btn btn-jk-accent w-100">Predict Price</button>
            </div>
          </form>
        </div>
      </div>

      {% if result %}
      <div class="alert alert-success mt-4 mb-0">
        <h5 class="mb-2">Estimated Value: ₹{{ "{:,.0f}".format(result.estimated_value) }}</h5>
        <div>Range: ₹{{ "{:,.0f}".format(result.price_range_low) }} - ₹{{ "{:,.0f}".format(result.price_range_high) }}</div>
        <div>Per sq.ft: ₹{{ "{:,.0f}".format(result.per_sqft) }} ({{ result.method }})</div>
      </div>
      {% endif %}
    </div>
  </div>
</section>
{% endblock %}
""",
    "public/saved.html": """{% extends "public/base.html" %}
{% block title %}Saved Properties{% endblock %}
{% block content %}
<div class="container py-5 jk-flow">
  <h1 class="section-title">Saved Properties</h1>
  <div id="savedList" class="row g-4"></div>
</div>
{% endblock %}
{% block extra_js %}
<script>
(async () => {
  const r = await fetch('/api/saved');
  const d = await r.json();
  const el = document.getElementById('savedList');
  if (!d.properties?.length) { el.innerHTML = '<p class="text-muted">No saved properties yet.</p>'; return; }
  el.innerHTML = d.properties.map(p => `
    <div class="col-md-4"><div class="card property-card"><div class="card-body">
      <h5><a href="/property/${p.slug}">${p.property_name}</a></h5>
      <p>${p.area_name} — ₹${p.price.toLocaleString('en-IN')}</p>
    </div></div></div>`).join('');
})();
</script>
{% endblock %}
""",
    "public/sell_property.html": """{% extends "public/base.html" %}

{% block title %}Sell Your Property - {{ company_name }}{% endblock %}

{% block content %}

<section class="container py-4 py-md-5 jk-flow sell-page">

  <header class="mb-4">

    <h1 class="section-title">Sell / Rent Your Property</h1>

    <p class="text-muted mb-0">

      Submit your listing details. Every submission is marked as <strong>Pending Approval</strong> and

      becomes public only after admin verification.

    </p>

  </header>



  <form method="POST" enctype="multipart/form-data" class="submission-form card p-3 p-md-4 p-lg-5" id="sellPropertyForm">

    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">



    <div class="mb-4">
      <label class="form-label fw-semibold">Listing Intent *</label>
      <input type="hidden" id="listingIntentInput" name="listing_intent" value="sell">
      <div class="sell-option-chips sell-intent-chips" role="group" aria-label="Listing intent">
        <button type="button" class="sell-option-chip btn-orange is-active" data-listing-intent="sell">Sell Property</button>
        <button type="button" class="sell-option-chip" data-listing-intent="rent">Rent Property</button>
      </div>
    </div>

    <h5 class="mb-3" id="contactSectionTitle">Owner Details (Mandatory)</h5>

    <div class="row g-3 sell-contact-row">

      <div class="col-12">

        <label class="form-label">Seller Type *</label>

        <input type="hidden" id="submitterTypeInput" name="submitter_type" value="owner">
        <input type="hidden" id="sellerTypeInput" name="seller_type" value="owner">

        <div class="sell-option-chips" role="group" aria-label="Seller type">

          <button type="button" class="sell-option-chip is-active" data-submitter-type="owner">Owner</button>

          <button type="button" class="sell-option-chip" data-submitter-type="broker">Broker</button>

          <button type="button" class="sell-option-chip" data-submitter-type="developer">Developer</button>

        </div>

      </div>

      <div class="col-12 col-md-6 sell-contact-field">

        <label class="form-label" for="contactNameInput" id="contactNameLabel">Owner Name *</label>

        <input class="form-control" id="contactNameInput" name="owner_name" placeholder="Owner Name *" required>

      </div>

      <div class="col-12 col-md-6 sell-contact-field">

        <label class="form-label" for="ownerMobileInput">Mobile Number *</label>

        <input class="form-control" id="ownerMobileInput" name="owner_mobile" type="tel" inputmode="tel" autocomplete="tel" placeholder="10-digit mobile number" minlength="10" maxlength="15" required>

      </div>

      <div class="col-12 col-md-6 sell-contact-field">

        <label class="form-label" for="ownerAltMobileInput">Alternate Mobile</label>

        <input class="form-control" id="ownerAltMobileInput" name="owner_alt_mobile" type="tel" inputmode="tel" autocomplete="tel" placeholder="Alternate mobile (optional)" maxlength="15">

      </div>

      <div class="col-12 col-md-6 sell-contact-field">

        <label class="form-label" for="ownerEmailInput">Email Address</label>

        <input type="email" class="form-control" id="ownerEmailInput" name="owner_email" placeholder="Email address (optional)">

      </div>

      <div class="col-12 sell-contact-field">

        <label class="form-label" for="ownerAddressInput">Full Residential Address *</label>

        <textarea class="form-control" id="ownerAddressInput" name="owner_address" rows="2" placeholder="Full residential address *" required></textarea>

      </div>

    </div>



    <h5 class="mt-4 mb-3">Property Details</h5>



    <div class="row g-3">

      <div class="col-12 col-md-4">

        <label class="form-label" for="sellCitySelect">City *</label>

        <select class="form-select" id="sellCitySelect" name="city" required>

          {% for city in city_options %}

          <option value="{{ city }}" {% if city == 'Surat' %}selected{% endif %}>{{ city }}</option>

          {% endfor %}

        </select>

      </div>

      <div class="col-12 col-md-8">

        <label class="form-label" for="sellLocationInput">Location / Area *</label>

        <input class="form-control" id="sellLocationInput" name="location_area" list="suratLocalities" placeholder="e.g. Vesu, Adajan, Pal, Piplod" required autocomplete="off">

        <datalist id="suratLocalities">

          {% for loc in surat_localities %}

          <option value="{{ loc }}"></option>

          {% endfor %}

        </datalist>

      </div>



      <div class="col-12">

        <label class="form-label">Property Type *</label>

        <input type="hidden" id="propertyTypeInput" name="property_type" value="">

        <div class="sell-option-chips sell-property-type-chips" role="group" aria-label="Property type">

          <button type="button" class="sell-option-chip" data-property-type="apartment">Apartment / Flat</button>

          <button type="button" class="sell-option-chip" data-property-type="villa">Villa</button>

          <button type="button" class="sell-option-chip" data-property-type="bungalow">Bungalow</button>

          <button type="button" class="sell-option-chip" data-property-type="plot">Plot / Land</button>

          <button type="button" class="sell-option-chip" data-property-type="shop">Shop</button>

          <button type="button" class="sell-option-chip" data-property-type="office">Office</button>

        </div>

        <div class="form-text">Select the type that best matches your property.</div>

      </div>



      <div class="col-12 col-md-6">

        <label class="form-label" for="propertyTitleInput">Property Title *</label>

        <input class="form-control" id="propertyTitleInput" name="property_title" placeholder="e.g. 3 BHK flat in Vesu" required>

      </div>



      <div class="col-12 col-sm-6 col-md-3" id="bhkWrap">

        <label class="form-label" for="bhkInput">BHK Number</label>

        <input class="form-control" id="bhkInput" type="number" name="bhk" min="0" placeholder="BHK">

      </div>



      <div class="col-12 col-sm-6 col-md-3 d-none" id="blockWingWrap">

        <label class="form-label" for="blockWingInput">Block / Wing</label>

        <input class="form-control" id="blockWingInput" name="block_wing" placeholder="e.g. A, B, C">

      </div>



      <div class="col-12 col-sm-6 col-md-3" id="unitNumberWrap">

        <label class="form-label" for="unitNumberInput" id="unitNumberLabel">Unit Number</label>

        <input class="form-control" id="unitNumberInput" name="unit_number" placeholder="e.g. 101, 903">

      </div>



      <div class="col-12 col-sm-6 col-md-3 d-none" id="apartmentNumberWrap">

        <label class="form-label" for="apartmentNumberInput">Apartment Number</label>

        <input class="form-control" id="apartmentNumberInput" name="apartment_number" placeholder="Apartment Number">

      </div>



      <div class="col-12 col-sm-6 col-md-3 d-none" id="flatNumberWrap">

        <label class="form-label" for="flatNumberInput">Flat Number</label>

        <input class="form-control" id="flatNumberInput" name="flat_number" placeholder="Flat Number">

      </div>

    </div>



    <h5 class="mt-4 mb-3">Area &amp; Expected Price</h5>

    <div class="row g-3 sell-area-price-row">

      <div class="col-12 col-md-6">

        <label class="form-label" for="areaValueInput" id="areaValueLabel">Enter the area in sqft *</label>

        <input class="form-control" id="areaValueInput" type="number" name="area_value" placeholder="Enter the area in sqft" required min="0.01" step="any">

        <label class="form-label mt-3">Area Unit *</label>

        <input type="hidden" id="areaUnitInput" name="area_unit" value="sq_ft">

        <div class="sell-option-chips" role="group" aria-label="Area unit">

          <button type="button" class="sell-option-chip is-active" data-area-unit="sq_ft">Sq. Ft.</button>

          <button type="button" class="sell-option-chip" data-area-unit="sq_yard">Sq. Yard</button>

          <button type="button" class="sell-option-chip" data-area-unit="vigha">Vigha</button>

          <button type="button" class="sell-option-chip" data-area-unit="sq_meter">Sq. Meter</button>

        </div>

        <input type="hidden" id="areaSqFtInput" name="area_sq_ft">

        <div class="form-text" id="areaConvertedHint"></div>

      </div>



      <div class="col-12 col-md-6">

        <label class="form-label" for="expectedPriceInput">Expected Price (INR) *</label>

        <input class="form-control" id="expectedPriceInput" type="number" name="price" placeholder="Enter expected price" min="1" step="1" required>

      </div>



      <div class="col-12">

        <label class="form-label" for="propertyAddressInput">Property Address *</label>

        <textarea class="form-control" id="propertyAddressInput" name="property_address" rows="2" placeholder="Full property address *" required></textarea>

      </div>

      <div class="col-12">

        <label class="form-label" for="descriptionInput">Property Description</label>

        <textarea class="form-control" id="descriptionInput" name="description" rows="4" placeholder="Describe your property (optional)"></textarea>

      </div>

    </div>



    <h5 class="mt-4 mb-3">Amenities</h5>

    <div class="row g-2">

      {% for amenity in ['Parking','Lift','Security','Power Backup','Garden','Gym','Swimming Pool','Club House','CCTV','Water Supply'] %}

      <div class="col-6 col-md-4 col-lg-3">

        <label class="amenity-check">

          <input type="checkbox" name="amenities" value="{{ amenity }}">

          <span>{{ amenity }}</span>

        </label>

      </div>

      {% endfor %}

    </div>



    <h5 class="mt-4 mb-3">Media Upload</h5>
    <div class="row g-3">
      <div class="col-12 col-md-6">
        <label class="form-label" for="sellImagesInput">Selected Photos List</label>
        <input class="form-control" id="sellImagesInput" type="file" name="images" accept="image/*" multiple>
        <div id="sellImagesPreview" class="media-file-list media-file-list--photos d-none" aria-live="polite"></div>
      </div>
      <div class="col-12 col-md-6">
        <label class="form-label" for="sellVideosInput">Selected Videos List</label>
        <input class="form-control" id="sellVideosInput" type="file" name="videos" accept="video/*" multiple>
        <div id="sellVideosPreview" class="media-file-list media-file-list--videos d-none" aria-live="polite"></div>
      </div>
    </div>



    <div class="d-flex flex-column flex-sm-row flex-wrap gap-2 mt-4">

      <button class="btn btn-jk-accent btn-lg w-100 w-sm-auto" type="submit" id="sellSubmitBtn">Submit For Selling</button>

      <a href="{{ url_for('public.listings') }}" class="btn btn-outline-secondary btn-lg w-100 w-sm-auto">Browse Listings</a>

    </div>

  </form>

</section>

{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/media_file_manager.js') }}"></script>
<script src="{{ url_for('static', filename='js/sell_property.js') }}"></script>
{% endblock %}

""",
    "public/services.html": """{% extends "public/base.html" %}
{% block title %}Services - {{ company_name }}{% endblock %}
{% block content %}
<section class="container py-5">
  <h1 class="section-title">Our Services</h1>
  <p class="text-muted">End-to-end property services for residential and commercial needs.</p>
  <div class="row g-4 mt-1">
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-house-check"></i><h6>Buy Property</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-house-add"></i><h6>Sell Property</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-key"></i><h6>Rent Property</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-building"></i><h6>Residential Consultancy</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-briefcase"></i><h6>Commercial Consultancy</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-graph-up-arrow"></i><h6>Investment Consultancy</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-file-earmark-text"></i><h6>Documentation Assistance</h6></article></div>
    <div class="col-md-6 col-lg-3"><article class="service-card"><i class="bi bi-currency-rupee"></i><h6>Property Valuation</h6></article></div>
  </div>
</section>
{% endblock %}
""",
    "public/testimonials.html": """{% extends "public/base.html" %}
{% block title %}Testimonials - {{ company_name }}{% endblock %}
{% block content %}
<section class="container py-5">
  <header class="reveal-on-scroll mb-4">
    <h1 class="section-title">Testimonials / Reviews</h1>
    <p class="text-muted mb-0">Visitors and customers can share real experiences and comment on reviews.</p>
  </header>

  <article class="card p-4 mb-4 content-card reveal-on-scroll">
    <h5 class="mb-3">Add Your Review</h5>
    <form id="reviewForm" class="row g-2">
      <div class="col-md-4"><input class="form-control" name="name" placeholder="Your Name *" required></div>
      <div class="col-md-3"><input class="form-control" name="location" placeholder="Your Location" value="Surat"></div>
      <div class="col-md-2">
        <select class="form-select" name="rating" required>
          {% for r in [5,4,3,2,1] %}
          <option value="{{ r }}">{{ r }} Star</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-12">
        <textarea class="form-control" name="review_text" rows="3" placeholder="Write your review..." required></textarea>
      </div>
      <div class="col-md-3 d-grid">
        <button class="btn btn-jk-accent" type="submit">Post Review</button>
      </div>
    </form>
  </article>

  <div class="row g-4 mt-1" id="reviewsList">
    {% for t in testimonials %}
    <div class="col-md-6 col-lg-4">
      <article class="testimonial-card h-100">
        <div class="text-warning mb-2">{% for _ in range(t.rating) %}<i class="bi bi-star-fill"></i>{% endfor %}</div>
        <p class="mb-3">"{{ t.review_text }}"</p>
        <h6 class="mb-1">{{ t.client_name }}</h6>
        <small class="text-muted">{{ t.client_location }}</small>

        <hr>
        <h6 class="small text-uppercase mb-2">Comments</h6>
        <div class="review-comments">
          {% for c in t.comments %}
          <div class="review-comment-item">
            <strong>{{ c.commenter_name }}</strong>
            <p class="mb-1 small">{{ c.comment_text }}</p>
          </div>
          {% else %}
          <p class="small text-muted mb-2">No comments yet.</p>
          {% endfor %}
        </div>
        <form class="reviewCommentForm mt-2" data-review-id="{{ t.id }}">
          <input class="form-control form-control-sm mb-2" name="name" placeholder="Your name" required>
          <textarea class="form-control form-control-sm mb-2" name="comment_text" rows="2" placeholder="Write a comment..." required></textarea>
          <button class="btn btn-sm btn-outline-dark" type="submit">Add Comment</button>
        </form>
      </article>
    </div>
    {% else %}
    <p class="text-muted">Testimonials will be published soon.</p>
    {% endfor %}
  </div>
</section>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/reviews.js') }}"></script>
{% endblock %}
""",
    "register.html": """{% extends "base.html" %}
{% block title %}Register — {{ app_name }}{% endblock %}
{% block content %}
<div class="container auth-container">
  <div class="auth-card">
    <h1>Create Account</h1>
    <form method="POST" action="{{ url_for('auth.register') }}">
      <div class="form-group">
        <label for="username">Username *</label>
        <input type="text" id="username" name="username" required>
      </div>
      <div class="form-group">
        <label for="email">Email *</label>
        <input type="email" id="email" name="email" required>
      </div>
      <div class="form-group">
        <label for="full_name">Full Name</label>
        <input type="text" id="full_name" name="full_name">
      </div>
      <div class="form-group">
        <label for="phone">Phone</label>
        <input type="tel" id="phone" name="phone">
      </div>
      <div class="form-group">
        <label for="password">Password *</label>
        <input type="password" id="password" name="password" required minlength="6">
      </div>
      <button type="submit" class="btn btn-primary btn-block">Register</button>
    </form>
    <p class="auth-footer">Already have an account? <a href="{{ url_for('auth.login') }}">Login</a></p>
  </div>
</div>
{% endblock %}
""",
    "schedule_visit.html": """{% extends "base.html" %}
{% block title %}Site Visits — {{ app_name }}{% endblock %}
{% block content %}
<div class="container section">
  <h1>My Site Visits</h1>
  {% if not current_user.is_authenticated %}
  <p>Please <a href="{{ url_for('auth.login') }}">login</a> to view and schedule visits.</p>
  {% else %}
  <div id="visitsList" class="visits-list"></div>
  {% endif %}
</div>
{% endblock %}
{% block extra_js %}
<script>
{% if current_user.is_authenticated %}
(async () => {
  const res = await fetch('/api/visits');
  const d = await res.json();
  const el = document.getElementById('visitsList');
  if (!d.visits?.length) {
    el.innerHTML = '<p class="text-muted">No visits scheduled yet. Browse properties and schedule a tour.</p>';
    return;
  }
  el.innerHTML = d.visits.map(v => `
    <article class="card visit-card">
      <h3>${v.property_title}</h3>
      <p>${v.city} — ${v.visit_date} at ${v.visit_time}</p>
      <span class="badge status-${v.status}">${v.status}</span>
      ${v.notes ? '<p>' + v.notes + '</p>' : ''}
    </article>
  `).join('');
})();
{% endif %}
</script>
{% endblock %}
""",
    "search.html": """{% extends "base.html" %}
{% block title %}Search — {{ app_name }}{% endblock %}
{% block content %}
<div class="container section">
  <h1>Property Search</h1>
  <form id="searchForm" class="search-filters card">
    <div class="filter-row">
      <div class="form-group">
        <label>Keyword</label>
        <input type="text" name="q" id="q" placeholder="Title, locality...">
      </div>
      <div class="form-group">
        <label>City</label>
        <input type="text" name="city" id="city" placeholder="Mumbai, Bangalore...">
      </div>
      <div class="form-group">
        <label>Type</label>
        <select name="type" id="type">
          <option value="">Any</option>
          <option value="apartment">Apartment</option>
          <option value="villa">Villa</option>
          <option value="house">House</option>
          <option value="plot">Plot</option>
          <option value="commercial">Commercial</option>
        </select>
      </div>
      <div class="form-group">
        <label>Listing</label>
        <select name="listing_type" id="listing_type">
          <option value="">Any</option>
          <option value="sale">Sale</option>
          <option value="rent">Rent</option>
        </select>
      </div>
      <div class="form-group">
        <label>Min Price (₹)</label>
        <input type="number" name="min_price" id="min_price">
      </div>
      <div class="form-group">
        <label>Max Price (₹)</label>
        <input type="number" name="max_price" id="max_price">
      </div>
      <div class="form-group">
        <label>Min Bedrooms</label>
        <input type="number" name="min_bedrooms" id="min_bedrooms" min="0">
      </div>
    </div>
    <button type="submit" class="btn btn-primary">Search</button>
  </form>

  <div id="searchResults" class="property-grid mt-2"></div>
</div>

<section class="container section card">
  <h2>Price Prediction (Random Forest)</h2>
  <form id="predictForm" class="filter-row">
    <div class="form-group"><label>Area (sqft)</label><input type="number" id="pred_area" value="1200" required></div>
    <div class="form-group"><label>Bedrooms</label><input type="number" id="pred_beds" value="2"></div>
    <div class="form-group"><label>City</label><input type="text" id="pred_city" value="Bangalore"></div>
    <div class="form-group"><label>Type</label>
      <select id="pred_type">
        <option value="apartment">Apartment</option>
        <option value="villa">Villa</option>
        <option value="house">House</option>
        <option value="plot">Plot</option>
      </select>
    </div>
    <button type="submit" class="btn btn-outline">Predict Price</button>
  </form>
  <div id="predictResult" class="predict-result"></div>
</section>
{% endblock %}
{% block extra_js %}
<script src="{{ url_for('static', filename='js/search.js') }}"></script>
{% endblock %}
""",
}

def loader():
    return DictLoader(TEMPLATES)
