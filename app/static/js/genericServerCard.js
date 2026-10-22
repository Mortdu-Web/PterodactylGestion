import { ServerCardBase } from './ServerCardBase.js';

class GenericServerCard extends ServerCardBase {
    get cssClass() { return 'generic-server-card'; }
}

customElements.define('generic-server-card', GenericServerCard);
