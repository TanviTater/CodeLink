export type DeviceType='pc'|'router'|'switch'|'server'
export type Device={id:string;type:DeviceType;name:string;x:number;y:number;interfaces:any[];routes:any[];services:any;firewall:any[]}
export type Link={id:string;source:string;target:string;sourceInterface:string;targetInterface:string;enabled:boolean;delayMs:number;lossPercent:number}
export type Topology={devices:Device[];links:Link[]}
export type SimResult={runId?:number;protocol:string;status:string;delivered:boolean;reason?:string|null;path:string[];events:any[];packets:any[];metrics:any;diagnostics:any[];elapsedMs:number;resolvedAddress?:string;transcript?:any[]}
