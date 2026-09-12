class ChoresCard extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._config = {};
    this._states = null;
    this._unsubscribe = null;
    this._currentPerson = null;
    this._personInitialized = false;
    this.attachShadow({ mode: 'open' });
  }

  setConfig(config) {
    if (!config) {
      throw new Error("Invalid configuration");
    }
    this._config = {
      title: config.title || null,
      only_state: config.only_state || null,
    };
  }

  getCardSize() {
    return 2;
  }

  getGridOptions() {
    return {
      min_rows: 2,
      columns: 12,
      min_columns: 6,
    };
  }

  connectedCallback() {
    var event = new CustomEvent('context-request', {
      bubbles: true,
      composed: true,
      cancelable: true,
    });
    event.context = 'states';
    event.subscribe = true;
    event.callback = this._updateStates;
    this.dispatchEvent(event);
    this._render();
  }

  _updateStates = (states, unsubscribe) => {
    this._unsubscribe = unsubscribe;
    this._states = states;
    this._render();
  }

  // Use hass.states as the source of truth since it has full attributes
  _getStates() {
    if (this._hass && this._hass.states) {
      return this._hass.states;
    }
    return this._states || {};
  }

  disconnectedCallback() {
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = undefined;
    }
  }

  // Keep hass for callService access and current user detection
  set hass(hass) {
    this._hass = hass;
    if (!this._personInitialized) {
      this._initCurrentPerson();
    }
    this._render();
  }

  _initCurrentPerson() {
    if (!this._hass || !this._hass.user) {
      return;
    }
    var userName = this._hass.user.name;
    if (userName) {
      var persons = this._getPersons();
      if (persons.length > 0) {
        var match = persons.find(function (p) {
          return p.name === userName;
        });
        if (match) {
          this._currentPerson = match.id;
        }
      }
    }
    this._personInitialized = true;
  }

  _getPersons() {
    var states = this._getStates();
    return Object.values(states)
      .filter(function (e) { return e.entity_id.startsWith('person.'); })
      .map(function (e) {
        return {
          id: e.entity_id,
          name: (e.attributes && e.attributes.friendly_name) || e.entity_id.replace('person.', ''),
        };
      })
      .sort(function (a, b) { return a.name.localeCompare(b.name); });
  }

  _getPersonName(entityId) {
    if (!entityId) return 'Unknown';
    var states = this._getStates();
    var state = states[entityId];
    if (state && state.attributes && state.attributes.friendly_name) {
      return state.attributes.friendly_name;
    }
    return entityId.replace('person.', '');
  }

  _getChores() {
    var states = this._getStates();
    var chores = Object.values(states)
      .filter(function (e) { return e.entity_id.startsWith('sensor.chores_'); });

    if (this._config.only_state) {
      chores = chores.filter(function (e) { return e.state === this._config.only_state; }, this);
    }

    chores.sort(function (a, b) {
      var order = { due: 0, pending: 1 };
      var oa = order[a.state] !== undefined ? order[a.state] : 2;
      var ob = order[b.state] !== undefined ? order[b.state] : 2;
      if (oa !== ob) return oa - ob;
      var aa = a.attributes.days_until_due;
      var ab = b.attributes.days_until_due;
      if (aa != null && ab != null) return aa - ab;
      return 0;
    });

    return chores;
  }

  async _markDone(entityId) {
    if (!this._hass) return;
    var data = { entity_id: entityId };
    if (this._currentPerson) {
      data.person = this._currentPerson;
    }
    try {
      await this._hass.callService('chores', 'mark_done', data);
    } catch (err) {
      console.error('Failed to mark chore done:', err);
    }
  }

  _render() {
    var root = this.shadowRoot;
    if (!root) return;

    var chores = this._getChores();

    if (chores.length === 0) {
      root.innerHTML = this._style() +
        '<div class="card">' +
          (this._config.title ? '<div class="header">' + this._escape(this._config.title) + '</div>' : '') +
          '<div class="empty">No chores here.</div>' +
        '</div>';
      return;
    }

    var rows = chores.map(function (e) { return this._renderRow(e); }, this).join('');

    root.innerHTML = this._style() +
      '<div class="card">' +
        (this._config.title ? '<div class="header">' + this._escape(this._config.title) + '</div>' : '') +
        '<div class="rows">' + rows + '</div>' +
      '</div>';

    var self = this;
    root.querySelectorAll('.btn-done').forEach(function (btn) {
      btn.addEventListener('click', function () {
        self._markDone(btn.dataset.entity);
      });
    });
  }

  _renderRow(entity) {
    var a = entity.attributes;
    var name = this._escape(a.friendly_name || entity.entity_id);
    var icon = a.icon || 'mdi:clipboard-check';
    var dueInfo = this._formatDue(entity.state, a.days_until_due);

    var assignees = (a.assignees || []).map(function (id) {
      return this._escape(this._getPersonName(id));
    }, this).join(', ');

    var lastDoneBy = '';
    if (a.last_done_by) {
      lastDoneBy = ' by ' + this._escape(this._getPersonName(a.last_done_by));
    }

    var btn = '<button class="btn-done" data-entity="' + this._escape(entity.entity_id) + '">Done</button>';

    return '<div class="row ' + entity.state + '">' +
      '<ha-icon icon="' + this._escape(icon) + '" class="icon"></ha-icon>' +
      '<div class="info">' +
        '<div class="name">' + name + '</div>' +
        '<div class="meta ' + entity.state + '">' + dueInfo + '</div>' +
        (assignees ? '<div class="assignees"><ha-icon icon="mdi:account-multiple" class="mini-icon"></ha-icon>' + assignees + '</div>' : '') +
        (a.last_done ? '<div class="last-done">Last done: ' + this._formatDate(a.last_done) + lastDoneBy + '</div>' : '') +
      '</div>' +
      btn +
    '</div>';
  }

  _formatDate(isoStr) {
    if (!isoStr) return 'Never';
    var d = new Date(isoStr);
    if (isNaN(d.getTime())) return 'Never';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  _formatDue(state, days) {
    if (days == null) return 'Due now';
    if (days < 0) return Math.abs(days) + (Math.abs(days) === 1 ? ' day overdue' : ' days overdue');
    if (days === 0) return 'Due today';
    if (days === 1) return 'Due tomorrow';
    return 'Due in ' + days + ' days';
  }

  _escape(str) {
    if (!str) return '';
    var div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  _style() {
    return '<style>' +
      ':host { display: block; }' +
      '.card {' +
        'background: var(--card-background-color, #fff);' +
        'border-radius: 12px;' +
        'box-shadow: 0 2px 8px rgba(0,0,0,0.08);' +
        'padding: 16px;' +
      '}' +
      '.header {' +
        'font-size: 1.2em;' +
        'font-weight: 500;' +
        'color: var(--primary-text-color);' +
        'margin-bottom: 12px;' +
      '}' +
      '.rows { display: flex; flex-direction: column; gap: 8px; }' +
      '.row {' +
        'display: flex;' +
        'align-items: center;' +
        'gap: 12px;' +
        'padding: 12px;' +
        'border-radius: 8px;' +
        'background: var(--secondary-background-color, rgba(0,0,0,0.03));' +
      '}' +
      '.row.due { border-left: 3px solid var(--error-color, #db4437); }' +
      '.row.pending { border-left: 3px solid var(--primary-color, #03a9f4); }' +
      '.icon { --mdc-icon-size: 24px; color: var(--secondary-text-color); flex-shrink: 0; }' +
      '.info { flex: 1; min-width: 0; }' +
      '.name { font-weight: 500; color: var(--primary-text-color); }' +
      '.meta { font-size: 0.85em; color: var(--secondary-text-color); margin-top: 2px; }' +
      '.meta.due { color: var(--error-color, #db4437); }' +
      '.meta.pending { color: var(--primary-color, #03a9f4); }' +
      '.assignees {' +
        'font-size: 0.8em;' +
        'color: var(--secondary-text-color);' +
        'margin-top: 2px;' +
        'display: flex;' +
        'align-items: center;' +
        'gap: 4px;' +
      '}' +
      '.mini-icon { --mdc-icon-size: 14px; opacity: 0.6; }' +
      '.last-done {' +
        'font-size: 0.8em;' +
        'color: var(--secondary-text-color);' +
        'margin-top: 2px;' +
        'opacity: 0.7;' +
      '}' +
      '.btn-done {' +
        'border: none;' +
        'border-radius: 8px;' +
        'padding: 8px 16px;' +
        'font-size: 0.85em;' +
        'font-weight: 500;' +
        'cursor: pointer;' +
        'background: var(--primary-color, #03a9f4);' +
        'color: #fff;' +
        'white-space: nowrap;' +
        'flex-shrink: 0;' +
      '}' +
      '.btn-done:hover { opacity: 0.85; }' +
      '.empty { text-align: center; color: var(--secondary-text-color); padding: 32px; }' +
    '</style>';
  }
}

customElements.define('chores-card', ChoresCard);
