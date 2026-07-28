#!/usr/bin/env python3
"""Generate the View Assist 'alerts' (persistent alert stack) view, v3.

Three render states, all built at render time from alert2 entities:
  1. Active (on + unacked) alerts -> full rows with DISMISS (alert2.ack).
  2. No active, but fired-and-never-acked history -> dimmed rows with
     per-row ACK plus an ACK ALL footer (alert2.ack_all).
  3. Nothing -> "No active alerts".

Emits alerts.yaml (fork, root-card format) and alerts_view.json (dashboard view).
"""
import json

import yaml

ROWS_JS = """[[[
  const EXCLUDE = ['alert2.alert2_error', 'alert2.alert2_warning', 'alert2.alert2_global_exception'];
  const RANK = {high: 0, medium: 1, low: 2};
  const COLOR = {high: '#ff5252', medium: '#ffb300', low: '#66bb6a'};

  const row = (e, active) => {
    const when = e.attributes.last_on_time || e.attributes.last_fired_time;
    const ts = when ? new Date(when).toLocaleString([], {weekday: 'short', hour: '2-digit', minute: '2-digit'}) : '';
    const msg = e.attributes.last_fired_message || '';
    return {
      type: 'custom:button-card',
      entity: e.entity_id,
      show_icon: false, show_name: false, show_state: false,
      styles: {
        grid: [
          {'grid-template-areas': '"icon name dismiss" "icon msg dismiss"'},
          {'grid-template-columns': '12vh 1fr 24vh'},
          {'grid-template-rows': 'min-content min-content'},
          {'column-gap': '2vh'}
        ],
        card: [
          {'background-color': 'rgba(0,0,0,0.35)'},
          {border: 'none'}, {'border-radius': '1vw'},
          {padding: '2vh'}, {'margin-bottom': '1.5vh'},
          {opacity: active ? 1 : 0.55}
        ],
        custom_fields: {
          icon: [{'grid-area': 'icon'}, {'align-self': 'center'}, {'justify-self': 'center'},
                 {color: active ? (COLOR[e.attributes.priority] || '#ffb300') : '#b0b0b0'}],
          name: [{'grid-area': 'name'}, {'justify-self': 'start'}, {'align-self': 'end'},
                 {'font-size': '4.5vh'}, {'font-weight': 500}, {'text-align': 'left'}],
          msg: [{'grid-area': 'msg'}, {'justify-self': 'start'}, {'align-self': 'start'},
                {'font-size': '3vh'}, {'font-weight': 300}, {opacity: 0.85}, {'text-align': 'left'}],
          dismiss: [{'grid-area': 'dismiss'}, {'align-self': 'center'},
                    {'justify-self': 'stretch'}, {height: '100%'}]
        }
      },
      custom_fields: {
        icon: `<ha-icon icon="${e.attributes.icon || 'mdi:alert-circle'}" style="--mdc-icon-size: 8vh;"></ha-icon>`,
        name: e.attributes.friendly_name || e.entity_id,
        msg: active ? msg : `Cleared · ${ts}${msg ? ' — ' + msg : ''}`,
        dismiss: {card: {
          type: 'custom:button-card',
          name: active ? 'DISMISS' : 'ACK',
          tap_action: {action: 'call-service', service: 'alert2.ack', target: {entity_id: e.entity_id}},
          styles: {
            card: [{'background-color': 'rgba(0,0,0,0.45)'}, {border: 'none'},
                   {'border-radius': '1vw'}, {height: '100%'}, {'min-height': '12vh'}],
            name: [{'font-size': '3.5vh'}, {'font-weight': 500}, {'letter-spacing': '0.1em'}]
          }
        }}
      }
    };
  };

  const hero = (e) => ({
    type: 'custom:button-card',
    entity: e.entity_id,
    show_icon: false, show_name: false, show_state: false,
    styles: {
      grid: [
        {'grid-template-areas': '"icon name" "icon msg" "dismiss dismiss"'},
        {'grid-template-columns': 'min-content 1fr'},
        {'grid-template-rows': 'min-content min-content min-content'},
        {'column-gap': '5vh'}, {'row-gap': '1vh'}
      ],
      card: [{background: 'none'}, {border: 'none'}, {padding: '4vh'}, {'margin-top': '4vh'}],
      custom_fields: {
        icon: [{'grid-area': 'icon'}, {'align-self': 'center'}, {'justify-self': 'end'},
               {'border-right': '2px solid rgba(255,255,255,0.6)'}, {'padding-right': '6vh'},
               {color: 'white'}],
        name: [{'grid-area': 'name'}, {'justify-self': 'start'}, {'align-self': 'end'},
               {'font-size': '12vh'}, {'font-weight': 500}, {'text-align': 'left'}],
        msg: [{'grid-area': 'msg'}, {'justify-self': 'start'}, {'align-self': 'start'},
              {'font-size': '6.5vh'}, {'font-weight': 300}, {opacity: 0.9}, {'text-align': 'left'},
              {'text-wrap': 'balance'}],
        dismiss: [{'grid-area': 'dismiss'}, {'justify-self': 'center'}, {'margin-top': '8vh'},
                  {width: '55%'}]
      }
    },
    custom_fields: {
      icon: `<ha-icon icon="${e.attributes.icon || 'mdi:alert-circle'}" style="--mdc-icon-size: 30vh; margin: 0;"></ha-icon>`,
      name: e.attributes.friendly_name || e.entity_id,
      msg: e.attributes.last_fired_message || '',
      dismiss: {card: {
        type: 'custom:button-card',
        name: 'DISMISS',
        tap_action: {action: 'call-service', service: 'alert2.ack', target: {entity_id: e.entity_id}},
        styles: {
          card: [{'background-color': 'rgba(0,0,0,0.45)'}, {border: 'none'},
                 {'border-radius': '1vw'}, {'min-height': '16vh'}],
          name: [{'font-size': '5.5vh'}, {'font-weight': 500}, {'letter-spacing': '0.1em'}]
        }
      }}
    }
  });

  const all = Object.values(hass.states)
    .filter(e => e.entity_id.startsWith('alert2.') && !EXCLUDE.includes(e.entity_id) && !e.attributes.is_acked);
  const active = all.filter(e => e.state === 'on')
    .sort((a, b) => {
      const r = (RANK[a.attributes.priority] ?? 1) - (RANK[b.attributes.priority] ?? 1);
      if (r) return r;
      return (b.attributes.last_on_time || '').localeCompare(a.attributes.last_on_time || '');
    });

  if (active.length === 1) return [hero(active[0])];
  if (active.length) return active.map(e => row(e, true));

  const cleared = all.filter(e => e.state === 'off' && e.attributes.last_fired_time)
    .sort((a, b) => (b.attributes.last_fired_time || '').localeCompare(a.attributes.last_fired_time || ''));

  if (cleared.length) {
    return [...cleared.map(e => row(e, false)), {
      type: 'custom:button-card',
      name: 'ACK ALL',
      tap_action: {action: 'call-service', service: 'alert2.ack_all'},
      styles: {
        card: [{'background-color': 'rgba(0,0,0,0.45)'}, {border: 'none'},
               {'border-radius': '1vw'}, {'min-height': '10vh'}, {'margin-top': '1vh'}],
        name: [{'font-size': '3.5vh'}, {'font-weight': 500}, {'letter-spacing': '0.1em'}]
      }
    }];
  }

  return [{
    type: 'custom:button-card',
    show_icon: false, show_name: false,
    styles: {
      grid: [{'grid-template-areas': '"empty"'}, {'grid-template-columns': '1fr'}],
      card: [{background: 'none'}, {border: 'none'}, {'padding-top': '10vh'}],
      custom_fields: {empty: [{'grid-area': 'empty'}, {'justify-self': 'stretch'}, {width: '100%'},
                              {'font-size': '5vh'}, {'font-weight': 300}, {opacity: 0.7}]}
    },
    custom_fields: {empty: '<div style="display:flex; align-items:center; justify-content:center; width:100%;"><ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 7vh; margin: 0;"></ha-icon>&nbsp; No active alerts</div>'}
  }];
]]]"""

BG_JS = """[[[
  const EXCLUDE = ['alert2.alert2_error', 'alert2.alert2_warning', 'alert2.alert2_global_exception'];
  const RANK = {high: 3, medium: 2, low: 1};
  const BG = {3: '#8f1f1f', 2: '#9a5b00', 1: '#0b5d8f'};
  let best = 0;
  for (const e of Object.values(hass.states)) {
    if (!e.entity_id.startsWith('alert2.') || EXCLUDE.includes(e.entity_id)) continue;
    if (e.state !== 'on' || e.attributes.is_acked) continue;
    best = Math.max(best, RANK[e.attributes.priority] ?? 2);
  }
  return best ? BG[best] : '#1c1c1c';
]]]"""

root_card = {
    "type": "custom:button-card",
    "variables": {"alertsstackversion": "3.2.1"},
    "template": ["variable_template", "body_template"],
    "triggers_update": "all",
    "custom_fields": {
        "title": "Alerts",
        "message": {
            "card": {
                "type": "custom:layout-card",
                "layout_type": "grid-layout",
                "layout": {
                    "margin": 0,
                    "card_margin": 0,
                    "grid-template-columns": "1fr",
                },
                "cards": ROWS_JS,
            }
        },
    },
    "styles": {
        "card": [{"background-color": BG_JS}, {"transition": "background-color 0.6s ease"}],
        "custom_fields": {
            "message": [
                {"grid-area": "message"},
                {"justify-self": "center"},
                {"align-self": "start"},
                {"width": "94%"},
                {"margin-top": "9vh"},
                {"max-height": "78vh"},
                {"overflow-y": "auto"},
            ]
        }
    },
}

view = {"type": "panel", "title": "Alerts", "path": "alert2", "cards": [root_card]}

with open("alert2_view_card.yaml", "w") as f:
    yaml.dump(root_card, f, sort_keys=False, allow_unicode=True, width=110)
with open("alerts_view.json", "w") as f:
    json.dump(view, f, indent=2)
with open("replace_view.txt", "w") as f:
    f.write(
        "for i in range(len(config['views'])):\n"
        "    if config['views'][i].get('path') in ('alerts', 'alert2'):\n"
        "        config['views'][i] = " + repr(view)
    )
print("wrote alerts.yaml, alerts_view.json, replace_view.txt (v3)")
