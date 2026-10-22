import { ServerCardBase } from './ServerCardBase.js';

class PalworldServerCard extends ServerCardBase {
    get cssClass() { return 'palworld-server-card'; }
}

customElements.define('palworld-server-card', PalworldServerCard);
