import {Badge,Button,Panel} from '../components/shared';
import type {ViewsProps} from './AgentViews';
export default function MyAgents({state,go,open}:ViewsProps){
  return <Panel title="My agents"><div className="settings-body">
    <div className="agent-identity"><div className="agent-symbol"><span/><span/></div><div><h3>Repeat Purchase Agent</h3><p className="muted">Same-product reorders within merchant-approved limits.</p></div></div>
    <div className="service-row"><div><Badge>{state?state.installed?'Installed · demo':'Setup required':'Development engine pending'}</Badge><p className="field-help">Dashboard, Activity and Settings share one customer journey.</p></div><Button primary onClick={()=>go('dashboard')}>Open agent</Button></div>
    {state&&!state.installed&&<Button onClick={()=>open('install')}>Continue installation</Button>}
  </div></Panel>;
}
