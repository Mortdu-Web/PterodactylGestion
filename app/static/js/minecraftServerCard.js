import { ServerCardBase } from './ServerCardBase.js';

class MinecraftServerCard extends ServerCardBase {
    get cssClass() { return 'minecraft-server-card'; }
}

customElements.define('minecraft-server-card', MinecraftServerCard);
