import { poseidon, LEVELS } from "./crypto.js";

export class MerkleTree {
  leaves: bigint[] = [];
  zeros: bigint[] | null = null;
  layersCache: bigint[][] = [];

  async init() {
    if (this.zeros) return;
    this.zeros = [0n];
    for (let i = 0; i < LEVELS; i++) this.zeros.push(await poseidon([this.zeros[i], this.zeros[i]]));
    this.layersCache = [this.leaves.slice()];
    for (let l = 0; l < LEVELS; l++) {
      const cur = this.layersCache[l], next = [];
      for (let i = 0; i < cur.length; i += 2) {
        next.push(await poseidon([cur[i], i + 1 < cur.length ? cur[i + 1] : this.zeros[l]]));
      }
      this.layersCache.push(next);
    }
  }
  async root() {
    await this.init();
    if (this.leaves.length === 0) return this.zeros![LEVELS];
    return this.layersCache[LEVELS][0] || this.zeros![LEVELS];
  }
  async path(index: number) {
    await this.init();
    const pathElements = [];
    let idx = index;
    for (let l = 0; l < LEVELS; l++) {
      const sib = idx ^ 1;
      pathElements.push(sib < this.layersCache[l].length ? this.layersCache[l][sib] : this.zeros![l]);
      idx >>= 1;
    }
    return { pathElements, pathIndices: index, root: this.layersCache[LEVELS][0] };
  }
  async insert(leaf: bigint) {
    await this.init();
    this.leaves.push(leaf);
    this.layersCache[0].push(leaf);
    let idx = this.leaves.length - 1;
    for (let l = 0; l < LEVELS; l++) {
        const sib = idx ^ 1;
        const left = sib > idx ? this.layersCache[l][idx] : (sib < this.layersCache[l].length ? this.layersCache[l][sib] : this.zeros![l]);
        const right = sib > idx ? (sib < this.layersCache[l].length ? this.layersCache[l][sib] : this.zeros![l]) : this.layersCache[l][idx];
        const p = await poseidon([left, right]);
        idx >>= 1;
        this.layersCache[l+1][idx] = p;
    }
  }
}
