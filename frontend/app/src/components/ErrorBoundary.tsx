import {Component, type ReactNode} from 'react';
import {Button, Empty} from './shared';

export default class ErrorBoundary extends Component<{children:ReactNode}, {failed:boolean}> {
  state={failed:false};
  static getDerivedStateFromError() { return {failed:true}; }
  render() {
    if(this.state.failed) return <main className="recovery-page"><Empty title="This workspace could not be displayed"
      action={<Button primary onClick={()=>window.location.reload()}>Reload workspace</Button>}>
      Your saved work remains on the server. Reload to restore your session and latest state.
    </Empty></main>;
    return this.props.children;
  }
}
