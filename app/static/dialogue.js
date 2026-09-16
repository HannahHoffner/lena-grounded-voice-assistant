/** Accessible renderer for LENA's server-bound clarification contract. */
(function () {
  "use strict";

  class DialogueUI {
    constructor(panel, prompt, choices, submit, onSubmit) {
      this.panel = panel;
      this.prompt = prompt;
      this.choices = choices;
      this.submit = submit;
      this.onSubmit = onSubmit;
      this.active = null;
      this.selected = new Set();
      this.busy = false;
      this.submit.addEventListener("click", () => this.sendSelected());
    }

    render(clarification) {
      this.busy = false;
      this.active = clarification || null;
      this.selected.clear();
      this.choices.replaceChildren();
      this.panel.hidden = !this.active;
      if (!this.active) return;
      this.prompt.textContent = this.active.prompt;
      this.submit.textContent = this.active.submit_label;
      this.submit.hidden = !this.active.multiple_facts_allowed || !this.active.choices.length;
      this.submit.disabled = true;
      for (const choice of this.active.choices) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "clarification-choice";
        button.textContent = choice.label;
        button.dataset.choiceValue = choice.value;
        button.setAttribute("aria-pressed", "false");
        button.addEventListener("click", () => this.choose(button, choice.value));
        this.choices.appendChild(button);
      }
      this.choices.querySelector("button")?.focus();
    }

    choose(button, value) {
      if (this.busy || !this.active) return;
      if (!this.active.multiple_facts_allowed) {
        this.disable();
        void this.onSubmit(this.active.dialog_id, [value]);
        return;
      }
      if (this.selected.has(value)) this.selected.delete(value);
      else this.selected.add(value);
      button.setAttribute("aria-pressed", String(this.selected.has(value)));
      this.submit.disabled = !this.selected.size;
    }

    sendSelected() {
      if (this.busy || !this.active || !this.selected.size) return;
      const values = Array.from(this.selected);
      this.disable();
      void this.onSubmit(this.active.dialog_id, values);
    }

    disable() {
      this.busy = true;
      for (const button of this.panel.querySelectorAll("button")) button.disabled = true;
    }

    restore() {
      this.busy = false;
      for (const button of this.choices.querySelectorAll("button")) button.disabled = false;
      this.submit.disabled = !this.selected.size;
    }

    clear() {
      this.active = null;
      this.selected.clear();
      this.busy = false;
      this.choices.replaceChildren();
      this.panel.hidden = true;
    }

    relocalize(copy) {
      if (!this.active) return;
      const wasBusy = this.busy;
      this.active.prompt = copy.prompts[this.active.type] || this.active.prompt;
      this.active.submit_label = copy.submit_label || this.active.submit_label;
      for (const choice of this.active.choices) {
        choice.label = copy.choices[choice.value] || choice.label;
      }
      this.render(this.active);
      if (wasBusy) this.disable();
    }
  }

  window.LenaDialogueUI = DialogueUI;
})();
