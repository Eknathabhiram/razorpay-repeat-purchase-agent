import { createContext, useContext, useEffect, useId, useRef, useSyncExternalStore, type ReactNode } from 'react';
export const CommandErrorContext=createContext('');
function subscribeOnline(callback:()=>void) {
  window.addEventListener('online',callback);window.addEventListener('offline',callback);
  return ()=>{window.removeEventListener('online',callback);window.removeEventListener('offline',callback);};
}
export function useOnline() { return useSyncExternalStore(subscribeOnline,()=>navigator.onLine); }
export function Icon({ name = 'arrow' }: { name?: string }) {
  const paths: Record<string, string> = {
    home:'m3 10 9-7 9 7v10H3z M9 20v-7h6v7', grid:'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
    activity:'M3 12h4l3-7 4 14 3-7h4', settings:'M3 6h18 M3 12h18 M3 18h18 M8 3v6 M16 9v6 M10 15v6',
    link:'m10 14 4-4 M8 16l-1 1a4 4 0 0 1-6-6l5-5a4 4 0 0 1 6 0 M16 8l1-1a4 4 0 0 1 6 6l-5 5a4 4 0 0 1-6 0',
    close:'m6 6 12 12 M18 6 6 18', menu:'M4 6h16 M4 12h16 M4 18h16', arrow:'M4 12h16 m-6-6 6 6-6 6',
    pause:'M8 5v14 M16 5v14', check:'m5 12 4 4L19 6', box:'m12 3 9 5v9l-9 5-9-5V8z M3 8l9 5 9-5 M12 13v9',
  };
  return <svg className="icon" viewBox="0 0 24 24" aria-hidden="true"><path d={paths[name] ?? paths.arrow}/></svg>;
}
export function Button({children,onClick,primary=false,disabled=false,type='button'}:{
  children:ReactNode;onClick?:()=>void;primary?:boolean;disabled?:boolean;type?:'button'|'submit'
}) { return <button type={type} className={'button '+(primary?'primary':'secondary')} onClick={onClick} disabled={disabled}>{children}</button>; }
export function Badge({children,tone=''}:{children:ReactNode;tone?:string}) {return <span className={'badge '+tone}>{children}</span>;}
export function Panel({title,children,action}:{title:string;children:ReactNode;action?:ReactNode}) {
  return <section className="panel"><div className="panel-heading"><h2>{title}</h2>{action}</div>{children}</section>;
}
export function Empty({title,children,action}:{title:string;children:ReactNode;action?:ReactNode}) {
  return <div className="empty-view"><div className="empty-icon"><Icon name="box"/></div><h3>{title}</h3><p>{children}</p>{action}</div>;
}
export function Loading({label='Loading your workspace…'}:{label?:string}) {
  return <div className="loading-view" role="status"><span className="loading-indicator" aria-hidden="true"/><p>{label}</p><div className="loading-placeholder" aria-hidden="true"><i/><i/><i/></div></div>;
}
export function RefreshNotice({failed,onRetry}:{failed:boolean;onRetry:()=>void}) {
  return failed?<div className="notice warning" role="alert"><p>Updates are unavailable. Showing the last loaded data; refresh before approving changes.</p><Button onClick={onRetry}>Try again</Button></div>:null;
}
export function Dialog({title,children,footer,onClose,drawer=false}:{title:string;children:ReactNode;footer?:ReactNode;onClose:()=>void;drawer?:boolean}) {
  const titleId=useId();
  const commandError=useContext(CommandErrorContext);
  const ref=useRef<HTMLDialogElement>(null), closeRef=useRef<HTMLButtonElement>(null);
  useEffect(()=>{
    const previous=document.activeElement as HTMLElement|null;
    const previousOverflow=document.body.style.overflow;
    document.body.style.overflow='hidden';
    ref.current?.showModal();closeRef.current?.focus();
    const dialog=ref.current;
    return ()=>{if(dialog?.open)dialog.close();document.body.style.overflow=previousOverflow;if(previous?.isConnected)previous.focus();};
  },[]);
  return <dialog ref={ref} className={drawer?'drawer':'modal'} aria-labelledby={titleId} onCancel={e=>{e.preventDefault();onClose();}}>
    <div className={drawer?'drawer-header':'modal-header'}><h2 id={titleId}>{title}</h2><button ref={closeRef} type="button" className="icon-button" onClick={onClose} aria-label="Close details"><Icon name="close"/></button></div>
    <div className={drawer?'drawer-content':'modal-content'}>{commandError&&<p className="notice warning" role="alert">{commandError}</p>}{children}</div>
    {footer&&<div className={drawer?'drawer-footer':'modal-footer'}>{footer}</div>}
  </dialog>;
}
