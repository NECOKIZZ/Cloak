declare module 'circomlibjs' {
    export function buildPoseidon(): Promise<any>;
}

declare module 'snarkjs' {
    export const groth16: {
        fullProve(input: any, wasmFile: any, zkeyFileName: any, logger?: any): Promise<{ proof: any; publicSignals: any }>;
        verify(vKey: any, publicSignals: any, proof: any, logger?: any): Promise<boolean>;
    };
}
