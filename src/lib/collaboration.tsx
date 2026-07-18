/**
 * Collaboration Infrastructure
 * 
 * Design infrastructure for future multi-user functionality including:
 * - User roles and permissions
 * - Workspace sharing
 * - Comments and mentions
 * - Shared strategies and journals
 */

import { createContext, useContext, useState, useCallback, type ReactNode } from 'react';

// Types
export type UserRole = 'owner' | 'admin' | 'editor' | 'viewer';

export type Permission =
  | 'view_workspace'
  | 'edit_workspace'
  | 'delete_workspace'
  | 'share_workspace'
  | 'view_trades'
  | 'create_trades'
  | 'delete_trades'
  | 'view_strategies'
  | 'edit_strategies'
  | 'delete_strategies'
  | 'view_journal'
  | 'edit_journal'
  | 'manage_members'
  | 'manage_settings'
  | 'view_audit_log';

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: UserRole;
  joinedAt: number;
}

export interface WorkspaceMember {
  userId: string;
  email: string;
  name: string;
  avatar?: string;
  role: UserRole;
  invitedAt: number;
  invitedBy: string;
  status: 'pending' | 'accepted' | 'declined';
}

export interface Comment {
  id: string;
  userId: string;
  userName: string;
  userAvatar?: string;
  content: string;
  mentions: string[];
  tradeId?: string;
  strategyId?: string;
  createdAt: number;
  updatedAt?: number;
  replies?: Comment[];
}

export interface SharedEntity {
  id: string;
  type: 'workspace' | 'strategy' | 'journal';
  name: string;
  ownerId: string;
  ownerName: string;
  sharedWith: WorkspaceMember[];
  createdAt: number;
  updatedAt: number;
}

// Permission matrix
const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  owner: [
    'view_workspace', 'edit_workspace', 'delete_workspace', 'share_workspace',
    'view_trades', 'create_trades', 'delete_trades',
    'view_strategies', 'edit_strategies', 'delete_strategies',
    'view_journal', 'edit_journal',
    'manage_members', 'manage_settings', 'view_audit_log',
  ],
  admin: [
    'view_workspace', 'edit_workspace', 'share_workspace',
    'view_trades', 'create_trades', 'delete_trades',
    'view_strategies', 'edit_strategies',
    'view_journal', 'edit_journal',
    'manage_members', 'view_audit_log',
  ],
  editor: [
    'view_workspace', 'edit_workspace',
    'view_trades', 'create_trades',
    'view_strategies', 'edit_strategies',
    'view_journal', 'edit_journal',
  ],
  viewer: [
    'view_workspace',
    'view_trades',
    'view_strategies',
    'view_journal',
  ],
};

// Context
interface CollaborationContextValue {
  // Current user
  currentUser: User | null;
  setCurrentUser: (user: User | null) => void;
  
  // Workspace members
  members: WorkspaceMember[];
  addMember: (email: string, role: UserRole) => Promise<boolean>;
  removeMember: (userId: string) => void;
  updateMemberRole: (userId: string, role: UserRole) => void;
  
  // Comments
  comments: Comment[];
  addComment: (comment: Omit<Comment, 'id' | 'createdAt'>) => void;
  updateComment: (id: string, content: string) => void;
  deleteComment: (id: string) => void;
  getCommentsByTrade: (tradeId: string) => Comment[];
  
  // Shared entities
  sharedEntities: SharedEntity[];
  shareEntity: (entity: Omit<SharedEntity, 'id' | 'createdAt' | 'updatedAt'>) => string;
  unshareEntity: (id: string) => void;
  getSharedWithMe: () => SharedEntity[];
  
  // Permissions
  hasPermission: (permission: Permission) => boolean;
  getUserPermissions: (role: UserRole) => Permission[];
  canEdit: () => boolean;
  canView: () => boolean;
  canManage: () => boolean;
  
  // Sharing
  generateShareLink: (entityId: string, entityType: string) => string;
  inviteByEmail: (email: string, role: UserRole) => Promise<boolean>;
}

const CollaborationContext = createContext<CollaborationContextValue | null>(null);

export function useCollaboration() {
  const context = useContext(CollaborationContext);
  if (!context) {
    throw new Error('useCollaboration must be used within CollaborationProvider');
  }
  return context;
}

// Provider
export function CollaborationProvider({ children }: { children: ReactNode }) {
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [comments, setComments] = useState<Comment[]>([]);
  const [sharedEntities, setSharedEntities] = useState<SharedEntity[]>([]);

  // Permission checks
  const hasPermission = useCallback((permission: Permission): boolean => {
    if (!currentUser) return false;
    return ROLE_PERMISSIONS[currentUser.role].includes(permission);
  }, [currentUser]);

  const getUserPermissions = useCallback((role: UserRole): Permission[] => {
    return ROLE_PERMISSIONS[role];
  }, []);

  const canEdit = useCallback((): boolean => {
    return hasPermission('edit_workspace') || hasPermission('edit_journal');
  }, [hasPermission]);

  const canView = useCallback((): boolean => {
    return hasPermission('view_workspace');
  }, [hasPermission]);

  const canManage = useCallback((): boolean => {
    return hasPermission('manage_members');
  }, [hasPermission]);

  // Member management
  const addMember = useCallback(async (email: string, role: UserRole): Promise<boolean> => {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 500));
    
    const newMember: WorkspaceMember = {
      userId: `user-${Date.now()}`,
      email,
      name: email.split('@')[0],
      role,
      invitedAt: Date.now(),
      invitedBy: currentUser?.id || 'system',
      status: 'pending',
    };
    
    setMembers(prev => [...prev, newMember]);
    return true;
  }, [currentUser]);

  const removeMember = useCallback((userId: string) => {
    setMembers(prev => prev.filter(m => m.userId !== userId));
  }, []);

  const updateMemberRole = useCallback((userId: string, role: UserRole) => {
    setMembers(prev => prev.map(m => 
      m.userId === userId ? { ...m, role } : m
    ));
  }, []);

  // Comments
  const addComment = useCallback((comment: Omit<Comment, 'id' | 'createdAt'>) => {
    const newComment: Comment = {
      ...comment,
      id: `comment-${Date.now()}`,
      createdAt: Date.now(),
    };
    setComments(prev => [...prev, newComment]);
  }, []);

  const updateComment = useCallback((id: string, content: string) => {
    setComments(prev => prev.map(c =>
      c.id === id ? { ...c, content, updatedAt: Date.now() } : c
    ));
  }, []);

  const deleteComment = useCallback((id: string) => {
    setComments(prev => prev.filter(c => c.id !== id));
  }, []);

  const getCommentsByTrade = useCallback((tradeId: string): Comment[] => {
    return comments.filter(c => c.tradeId === tradeId);
  }, [comments]);

  // Shared entities
  const shareEntity = useCallback((
    entity: Omit<SharedEntity, 'id' | 'createdAt' | 'updatedAt'>
  ): string => {
    const id = `shared-${Date.now()}`;
    const newEntity: SharedEntity = {
      ...entity,
      id,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setSharedEntities(prev => [...prev, newEntity]);
    return id;
  }, []);

  const unshareEntity = useCallback((id: string) => {
    setSharedEntities(prev => prev.filter(e => e.id !== id));
  }, []);

  const getSharedWithMe = useCallback((): SharedEntity[] => {
    if (!currentUser) return [];
    return sharedEntities.filter(e => 
      e.sharedWith.some(m => m.userId === currentUser.id)
    );
  }, [currentUser, sharedEntities]);

  // Sharing utilities
  const generateShareLink = useCallback((entityId: string, entityType: string): string => {
    const base = window.location.origin;
    return `${base}/share/${entityType}/${entityId}`;
  }, []);

  const inviteByEmail = useCallback(async (email: string, role: UserRole): Promise<boolean> => {
    return addMember(email, role);
  }, [addMember]);

  return (
    <CollaborationContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        members,
        addMember,
        removeMember,
        updateMemberRole,
        comments,
        addComment,
        updateComment,
        deleteComment,
        getCommentsByTrade,
        sharedEntities,
        shareEntity,
        unshareEntity,
        getSharedWithMe,
        hasPermission,
        getUserPermissions,
        canEdit,
        canView,
        canManage,
        generateShareLink,
        inviteByEmail,
      }}
    >
      {children}
    </CollaborationContext.Provider>
  );
}

// Permission Gate Component
interface PermissionGateProps {
  permission: Permission;
  children: ReactNode;
  fallback?: ReactNode;
}

export function PermissionGate({ permission, children, fallback = null }: PermissionGateProps) {
  const { hasPermission } = useCollaboration();
  
  if (hasPermission(permission)) {
    return <>{children}</>;
  }
  
  return <>{fallback}</>;
}

// Role Badge Component
export function RoleBadge({ role }: { role: UserRole }) {
  const roleStyles: Record<UserRole, { bg: string; text: string; label: string }> = {
    owner: { bg: 'bg-purple-500/20', text: 'text-purple-400', label: 'Owner' },
    admin: { bg: 'bg-blue-500/20', text: 'text-blue-400', label: 'Admin' },
    editor: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: 'Editor' },
    viewer: { bg: 'bg-slate-500/20', text: 'text-slate-400', label: 'Viewer' },
  };
  
  const style = roleStyles[role];
  
  return (
    <span className={`px-2 py-0.5 text-xs rounded-md ${style.bg} ${style.text}`}>
      {style.label}
    </span>
  );
}

// Members List Component
export function MembersList() {
  const { members, currentUser, removeMember, updateMemberRole: _updateMemberRole } = useCollaboration();
  
  return (
    <div className="space-y-3">
      {members.map(member => (
        <div key={member.userId} className="flex items-center justify-between p-3 bg-slate-800 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-slate-700 flex items-center justify-center">
              {member.avatar ? (
                <img src={member.avatar} alt={member.name} className="w-full h-full rounded-full" />
              ) : (
                <span className="text-lg font-medium text-slate-300">
                  {member.name.charAt(0).toUpperCase()}
                </span>
              )}
            </div>
            <div>
              <p className="font-medium text-white">{member.name}</p>
              <p className="text-sm text-slate-400">{member.email}</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            <RoleBadge role={member.role} />
            {currentUser?.role === 'owner' && member.userId !== currentUser.id && (
              <button
                onClick={() => removeMember(member.userId)}
                className="p-1 text-slate-400 hover:text-red-400 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>
      ))}
      
      {members.length === 0 && (
        <p className="text-center text-slate-500 py-4">No members yet</p>
      )}
    </div>
  );
}

// Comments Thread Component
interface CommentsThreadProps {
  tradeId?: string;
  strategyId?: string;
}

export function CommentsThread({ tradeId, strategyId }: CommentsThreadProps) {
  const { comments, addComment, currentUser, deleteComment } = useCollaboration();
  
  const relevantComments = comments.filter(c => 
    (tradeId && c.tradeId === tradeId) || 
    (strategyId && c.strategyId === strategyId)
  );
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.namedItem('comment') as HTMLInputElement;
    
    if (input.value.trim() && currentUser) {
      addComment({
        userId: currentUser.id,
        userName: currentUser.name,
        userAvatar: currentUser.avatar,
        content: input.value.trim(),
        mentions: [],
        tradeId,
        strategyId,
      });
      input.value = '';
    }
  };
  
  return (
    <div className="space-y-4">
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          name="comment"
          placeholder="Add a comment..."
          className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm placeholder-slate-500"
        />
        <button
          type="submit"
          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 transition-colors"
        >
          Post
        </button>
      </form>
      
      <div className="space-y-3">
        {relevantComments.map(comment => (
          <div key={comment.id} className="flex gap-3 p-3 bg-slate-800/50 rounded-lg">
            <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center flex-shrink-0">
              {comment.userAvatar ? (
                <img src={comment.userAvatar} alt={comment.userName} className="w-full h-full rounded-full" />
              ) : (
                <span className="text-sm font-medium text-slate-300">
                  {comment.userName.charAt(0).toUpperCase()}
                </span>
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-white text-sm">{comment.userName}</span>
                <span className="text-xs text-slate-500">
                  {new Date(comment.createdAt).toLocaleDateString()}
                </span>
              </div>
              <p className="text-sm text-slate-300 mt-1">{comment.content}</p>
            </div>
            {currentUser?.id === comment.userId && (
              <button
                onClick={() => deleteComment(comment.id)}
                className="p-1 text-slate-400 hover:text-red-400 transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        ))}
        
        {relevantComments.length === 0 && (
          <p className="text-center text-slate-500 py-4">No comments yet</p>
        )}
      </div>
    </div>
  );
}

// Share Dialog Component
interface ShareDialogProps {
  entityId: string;
  entityType: 'workspace' | 'strategy' | 'journal';
  entityName: string;
  onClose: () => void;
}

export function ShareDialog({ entityId, entityType, entityName: _entityName, onClose }: ShareDialogProps) {
  const { inviteByEmail, generateShareLink, currentUser: _currentUser } = useCollaboration();
  const [email, setEmail] = useState('');
  const [role, setRole] = useState<UserRole>('viewer');
  const [isInviting, setIsInviting] = useState(false);
  const [shareLink, setShareLink] = useState('');
  
  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim()) return;
    
    setIsInviting(true);
    await inviteByEmail(email.trim(), role);
    setEmail('');
    setIsInviting(false);
  };
  
  const handleCopyLink = () => {
    const link = generateShareLink(entityId, entityType);
    setShareLink(link);
    navigator.clipboard.writeText(link);
  };
  
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      
      <div className="relative bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-md p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Share {entityType}</h2>
        
        {/* Invite by email */}
        <form onSubmit={handleInvite} className="space-y-3 mb-6">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter email address"
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm placeholder-slate-500"
          />
          <div className="flex gap-3">
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
            >
              <option value="viewer">Viewer</option>
              <option value="editor">Editor</option>
              <option value="admin">Admin</option>
            </select>
            <button
              type="submit"
              disabled={isInviting || !email.trim()}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500 disabled:opacity-50 transition-colors"
            >
              {isInviting ? 'Inviting...' : 'Invite'}
            </button>
          </div>
        </form>
        
        {/* Copy link */}
        <div className="border-t border-slate-800 pt-4">
          <p className="text-sm text-slate-400 mb-2">Or copy a share link</p>
          <div className="flex gap-2">
            <input
              type="text"
              value={shareLink}
              readOnly
              placeholder="Click 'Copy Link' to generate"
              className="flex-1 px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white text-sm"
            />
            <button
              onClick={handleCopyLink}
              className="px-4 py-2 bg-slate-700 text-white rounded-lg text-sm font-medium hover:bg-slate-600 transition-colors"
            >
              Copy Link
            </button>
          </div>
        </div>
        
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
    </div>
  );
}

export default CollaborationProvider;
