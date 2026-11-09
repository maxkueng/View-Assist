#!/usr/bin/env python3
"""Generate the View Assist 'alerts' (persistent alert stack) view, v4.

Three render states, all built at render time from alert2 entities:
  1. Active (on + unacked) alerts -> full rows with dismiss (alert2.ack).
  2. No active, but fired-and-never-acked history -> dimmed rows with
     per-row ack plus an Ack All footer (alert2.ack_all).
  3. Nothing -> "No active alerts".

v4 restyles everything to match the timer cards in js_modules/timers.js
(viewassist.helpers.timerCards / singleTimerCard): same 90vw rounded rows
on rgba(0,0,0,0.7), vw-based fonts (name 3vw, detail 2vw), icon-only
action buttons fused to the row's right edge, and a single-alert hero
laid out like the single-timer card with a pill action button.

Emits alert2.yaml (fork, root-card format) and alert2_view.json (dashboard
view, consumed by deploy.py).
"""
import json
import os

import yaml

ROWS_JS = """[[[
  const EXCLUDE = ['alert2.alert2_error', 'alert2.alert2_warning', 'alert2.alert2_global_exception'];
  const RANK = {high: 0, medium: 1, low: 2};
  const COLOR = {high: '#ff5252', medium: '#ffb300', low: '#66bb6a'};

  const edgeButton = (e, active) => ({
    type: 'custom:button-card',
    name: active ? 'Dismiss' : 'Ack',
    icon: active ? 'mdi:bell-off' : 'mdi:check',
    show_name: false,
    tap_action: {action: 'call-service', service: 'alert2.ack', target: {entity_id: e.entity_id}},
    styles: {
      card: [
        {'justify-self': 'end'}, {'align-self': 'center'},
        {'border-radius': '0 3vh 3vh 0'}, {border: 'none'},
        {'background-color': active ? 'var(--red-color)' : 'var(--blue-color)'},
        {height: '20vh'}, {width: '10vw'}
      ],
      icon: [{color: 'white'}]
    }
  });

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
          {'grid-template-areas': '"icon name ack" "icon msg ack"'},
          {'grid-template-columns': '18vh 1fr 10vw'},
          {'grid-template-rows': '1fr 1fr'}
        ],
        card: [
          {'background-color': 'rgba(0, 0, 0, 0.7)'},
          {border: 'none'}, {'border-radius': '3vh'},
          {padding: '0'}, {margin: '0 auto 1.5vh auto'},
          {width: '90vw'},
          {opacity: active ? 1 : 0.55}
        ],
        custom_fields: {
          icon: [{'grid-area': 'icon'}, {'align-self': 'center'}, {'justify-self': 'center'},
                 {color: active ? (COLOR[e.attributes.priority] || '#ffb300') : '#b0b0b0'}],
          name: [{'grid-area': 'name'}, {'justify-self': 'start'}, {'align-self': 'end'},
                 {color: 'white'}, {'font-size': '3vw'}, {'text-align': 'left'}],
          msg: [{'grid-area': 'msg'}, {'justify-self': 'start'}, {'align-self': 'start'},
                {color: 'white'}, {'font-size': '2vw'}, {'font-weight': 300}, {opacity: 0.85},
                {'text-align': 'left'}],
          ack: [{'grid-area': 'ack'}, {'justify-self': 'end'}, {padding: '0'}]
        }
      },
      custom_fields: {
        icon: `<ha-icon icon="${e.attributes.icon || 'mdi:alert-circle'}" style="--mdc-icon-size: 15vh; margin: 0;"></ha-icon>`,
        name: e.attributes.friendly_name || e.entity_id,
        msg: active ? msg : `Cleared · ${ts}${msg ? ' — ' + msg : ''}`,
        ack: {card: edgeButton(e, active)}
      }
    };
  };

  const pillButton = (name, tap_action, width, height, font_size, extra_card_styles = []) => ({
    type: 'custom:button-card',
    name: name,
    tap_action: tap_action,
    styles: {
      card: [
        {'justify-content': 'center'}, {'align-items': 'center'},
        {width: width}, {'border-radius': '6vh'}, {height: height},
        {border: 'none'}, {'background-color': 'rgba(0, 0, 0, 0.45)'},
        ...extra_card_styles
      ],
      name: [{'font-size': font_size}, {color: 'white'}, {'font-weight': 'bold'}, {'text-align': 'center'}]
    }
  });

  const hero = (e) => ({
    type: 'custom:button-card',
    entity: e.entity_id,
    show_icon: false, show_name: false, show_state: false,
    styles: {
      grid: [
        {'grid-template-areas': '"icon name" "icon msg" "act act"'},
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
               {color: 'white'}, {'font-size': '6vw'}, {'text-align': 'left'}],
        msg: [{'grid-area': 'msg'}, {'justify-self': 'start'}, {'align-self': 'start'},
              {color: 'white'}, {'font-size': '4vw'}, {'font-weight': 300}, {opacity: 0.9},
              {'text-align': 'left'}, {'text-wrap': 'balance'}],
        act: [{'grid-area': 'act'}, {'justify-self': 'center'}, {'margin-top': '8vh'}]
      }
    },
    custom_fields: {
      icon: `<ha-icon icon="${e.attributes.icon || 'mdi:alert-circle'}" style="--mdc-icon-size: 30vh; margin: 0;"></ha-icon>`,
      name: e.attributes.friendly_name || e.entity_id,
      msg: e.attributes.last_fired_message || '',
      act: {card: pillButton('Dismiss', {action: 'call-service', service: 'alert2.ack', target: {entity_id: e.entity_id}}, '40vw', '12vh', '5vh')}
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
    const ackAll = pillButton('Ack All', {action: 'call-service', service: 'alert2.ack_all'},
      '30vw', '10vh', '4vh', [{'justify-self': 'center'}, {'margin-top': '2vh'}]);
    return [...cleared.map(e => row(e, false)), ackAll];
  }

  return [{
    type: 'custom:button-card',
    show_icon: false, show_name: false,
    styles: {
      grid: [{'grid-template-areas': '"empty"'}, {'grid-template-columns': '1fr'}],
      card: [{background: 'none'}, {border: 'none'}, {'padding-top': '10vh'}],
      custom_fields: {empty: [{'grid-area': 'empty'}, {'justify-self': 'stretch'}, {width: '100%'},
                              {color: 'white'}, {'font-size': '3.5vw'}, {'font-weight': 300}, {opacity: 0.7}]}
    },
    custom_fields: {empty: '<div style="display:flex; align-items:center; justify-content:center; width:100%;"><ha-icon icon="mdi:check-circle-outline" style="--mdc-icon-size: 3.5vw; margin: 0;"></ha-icon>&nbsp; No active alerts</div>'}
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
    "variables": {"alertsstackversion": "4.1.0"},
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
                    "justify-items": "center",
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

out = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(out, "alert2.yaml"), "w") as f:
    yaml.dump(root_card, f, sort_keys=False, allow_unicode=True, width=110)
with open(os.path.join(out, "alert2_view.json"), "w") as f:
    json.dump(view, f, indent=2)
print("wrote alert2.yaml, alert2_view.json")
