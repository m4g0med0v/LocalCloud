# Graph Report - frontend  (2026-05-29)

## Corpus Check
- Corpus is ~34,693 words - fits in a single context window. You may not need a graph.

## Summary
- 930 nodes · 1839 edges · 87 communities (43 shown, 44 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 73 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Quota Requests & Storage Admin|Quota Requests & Storage Admin]]
- [[_COMMUNITY_Audit Log Viewer|Audit Log Viewer]]
- [[_COMMUNITY_Node Sharing & Permissions API|Node Sharing & Permissions API]]
- [[_COMMUNITY_Admin Panel & Registration|Admin Panel & Registration]]
- [[_COMMUNITY_File Types & Preview|File Types & Preview]]
- [[_COMMUNITY_Error Boundary & UI Shell|Error Boundary & UI Shell]]
- [[_COMMUNITY_Admin Page Components|Admin Page Components]]
- [[_COMMUNITY_Share Dialog & Permissions|Share Dialog & Permissions]]
- [[_COMMUNITY_File Action Bar & Info Panel|File Action Bar & Info Panel]]
- [[_COMMUNITY_Upload & Media Preview|Upload & Media Preview]]
- [[_COMMUNITY_Search & Debounce|Search & Debounce]]
- [[_COMMUNITY_Node Info Panel & Quota Stats|Node Info Panel & Quota Stats]]
- [[_COMMUNITY_Build Config & Dependencies|Build Config & Dependencies]]
- [[_COMMUNITY_File Grid & Date Formatting|File Grid & Date Formatting]]
- [[_COMMUNITY_Dev Dependencies & ESLint|Dev Dependencies & ESLint]]
- [[_COMMUNITY_TypeScript Config|TypeScript Config]]
- [[_COMMUNITY_Shadcn Component Config|Shadcn Component Config]]
- [[_COMMUNITY_Auth Context & Public Links|Auth Context & Public Links]]
- [[_COMMUNITY_TS Compiler Options|TS Compiler Options]]
- [[_COMMUNITY_Quota Request Cards|Quota Request Cards]]
- [[_COMMUNITY_UI Module 20|UI Module 20]]
- [[_COMMUNITY_UI Module 21|UI Module 21]]
- [[_COMMUNITY_UI Module 22|UI Module 22]]
- [[_COMMUNITY_UI Module 23|UI Module 23]]
- [[_COMMUNITY_UI Module 24|UI Module 24]]
- [[_COMMUNITY_UI Module 25|UI Module 25]]
- [[_COMMUNITY_UI Module 26|UI Module 26]]
- [[_COMMUNITY_UI Module 27|UI Module 27]]
- [[_COMMUNITY_UI Module 28|UI Module 28]]
- [[_COMMUNITY_UI Module 29|UI Module 29]]
- [[_COMMUNITY_UI Module 30|UI Module 30]]
- [[_COMMUNITY_UI Module 31|UI Module 31]]
- [[_COMMUNITY_UI Module 32|UI Module 32]]
- [[_COMMUNITY_UI Module 33|UI Module 33]]
- [[_COMMUNITY_UI Module 34|UI Module 34]]
- [[_COMMUNITY_UI Module 35|UI Module 35]]
- [[_COMMUNITY_UI Module 36|UI Module 36]]
- [[_COMMUNITY_UI Module 37|UI Module 37]]
- [[_COMMUNITY_UI Module 38|UI Module 38]]
- [[_COMMUNITY_UI Module 39|UI Module 39]]
- [[_COMMUNITY_UI Module 40|UI Module 40]]
- [[_COMMUNITY_UI Module 41|UI Module 41]]
- [[_COMMUNITY_UI Module 42|UI Module 42]]
- [[_COMMUNITY_UI Module 43|UI Module 43]]
- [[_COMMUNITY_UI Module 44|UI Module 44]]
- [[_COMMUNITY_UI Module 45|UI Module 45]]
- [[_COMMUNITY_UI Module 46|UI Module 46]]
- [[_COMMUNITY_UI Module 47|UI Module 47]]
- [[_COMMUNITY_UI Module 48|UI Module 48]]
- [[_COMMUNITY_UI Module 49|UI Module 49]]
- [[_COMMUNITY_UI Module 50|UI Module 50]]
- [[_COMMUNITY_UI Module 51|UI Module 51]]
- [[_COMMUNITY_UI Module 52|UI Module 52]]
- [[_COMMUNITY_UI Module 54|UI Module 54]]
- [[_COMMUNITY_UI Module 55|UI Module 55]]
- [[_COMMUNITY_UI Module 56|UI Module 56]]
- [[_COMMUNITY_UI Module 57|UI Module 57]]
- [[_COMMUNITY_UI Module 58|UI Module 58]]
- [[_COMMUNITY_UI Module 59|UI Module 59]]
- [[_COMMUNITY_UI Module 60|UI Module 60]]
- [[_COMMUNITY_UI Module 61|UI Module 61]]
- [[_COMMUNITY_UI Module 62|UI Module 62]]
- [[_COMMUNITY_UI Module 63|UI Module 63]]
- [[_COMMUNITY_UI Module 64|UI Module 64]]
- [[_COMMUNITY_UI Module 65|UI Module 65]]
- [[_COMMUNITY_UI Module 66|UI Module 66]]
- [[_COMMUNITY_UI Module 67|UI Module 67]]
- [[_COMMUNITY_UI Module 68|UI Module 68]]
- [[_COMMUNITY_UI Module 69|UI Module 69]]
- [[_COMMUNITY_UI Module 70|UI Module 70]]
- [[_COMMUNITY_UI Module 71|UI Module 71]]
- [[_COMMUNITY_UI Module 72|UI Module 72]]
- [[_COMMUNITY_UI Module 73|UI Module 73]]
- [[_COMMUNITY_UI Module 74|UI Module 74]]
- [[_COMMUNITY_UI Module 75|UI Module 75]]
- [[_COMMUNITY_UI Module 76|UI Module 76]]
- [[_COMMUNITY_UI Module 77|UI Module 77]]
- [[_COMMUNITY_UI Module 78|UI Module 78]]
- [[_COMMUNITY_UI Module 79|UI Module 79]]
- [[_COMMUNITY_UI Module 80|UI Module 80]]
- [[_COMMUNITY_UI Module 81|UI Module 81]]
- [[_COMMUNITY_UI Module 82|UI Module 82]]
- [[_COMMUNITY_UI Module 83|UI Module 83]]
- [[_COMMUNITY_UI Module 84|UI Module 84]]
- [[_COMMUNITY_UI Module 85|UI Module 85]]
- [[_COMMUNITY_UI Module 86|UI Module 86]]

## God Nodes (most connected - your core abstractions)
1. `NodeListItem` - 39 edges
2. `Button` - 34 edges
3. `compilerOptions` - 20 edges
4. `nodesApi` - 19 edges
5. `formatBytes()` - 18 edges
6. `compilerOptions` - 16 edges
7. `FilesPage Component` - 16 edges
8. `Input` - 15 edges
9. `useInfoPanel()` - 15 edges
10. `Skeleton()` - 14 edges

## Surprising Connections (you probably didn't know these)
- `Frontend Entry HTML (index.html)` --conceptually_related_to--> `Types Barrel Export (index.ts)`  [INFERRED]
  frontend/index.html → frontend/src/types/index.ts
- `FilePreviewModal` --shares_data_with--> `uploadsApi`  [INFERRED]
  frontend/src/components/preview/FilePreviewModal.tsx → frontend/src/api/uploads.ts
- `useMyQuota Hook` --conceptually_related_to--> `UploadProvider`  [INFERRED]
  frontend/src/hooks/useQuota.ts → frontend/src/contexts/upload.tsx
- `Props` --references--> `NodeListItem`  [EXTRACTED]
  src/components/files/FileActionBar.tsx → src/types/nodes.ts
- `Props` --references--> `NodeListItem`  [EXTRACTED]
  src/components/files/FileGrid.tsx → src/types/nodes.ts

## Hyperedges (group relationships)
- **Authentication-guarded routing pattern: AuthProvider + ProtectedRoute + AppShell** — app_tsx_authprovider, app_tsx_protectedroute, app_tsx_appshell [EXTRACTED 1.00]
- **Root provider stack: ThemeProvider + QueryClientProvider + TooltipProvider + BrowserRouter** — main_tsx, main_tsx_themeprovider, main_tsx_queryclientprovider [EXTRACTED 1.00]
- **All API modules share single Axios instance from lib/api** — api_audit_ts_auditapi, api_auth_ts_authapi, api_downloads_ts_downloadsapi, api_files_ts_filesapi, api_folders_ts_foldersapi, api_nodes_ts_nodesapi, api_permissions_ts_permissionsapi, api_public_links_ts_publiclinksapi, api_quotas_ts_quotasapi, api_registration_ts_registrationapi, lib_api_instance [EXTRACTED 1.00]
- **API Layer - All REST Clients Using lib/api** — roles_rolesApi, tasks_tasksApi, trash_trashApi, uploads_uploadsApi, users_usersApi [EXTRACTED 1.00]
- **File Item Renderers (Grid and List Views)** — filegriditem_FileGridItem, filelistitem_FileListItem, fileicon_FileIcon [EXTRACTED 0.95]
- **File Action Components (Single and Multi Selection)** — fileactionbar_FileActionBar, filemultiactionbar_FileMultiActionBar, itemactions_ItemActions [INFERRED 0.90]
- **File Operation Dialogs** — createfolderdialog_CreateFolderDialog, deleteconfirmdialog_DeleteConfirmDialog, foldercolordialog_FolderColorDialog, files_RenameDialog, files_ShareDialog, files_MoveDialog [INFERRED 0.85]
- **Authentication Guard Components** — protectedroute_ProtectedRoute, changepassworddialog_ChangePasswordDialog, contexts_auth [INFERRED 0.85]
- **Folder Color LocalStorage Management** — foldercolordialog_getFolderColor, foldercolordialog_setFolderColor, foldercolordialog_FolderColorDialog [EXTRACTED 1.00]
- **File Operation Dialogs** — renamedialog_RenameDialog, movedialog_MoveDialog, sharedialog_ShareDialog, files_DeleteConfirmDialog, files_FolderColorDialog [INFERRED 0.95]
- **Application Shell Layout Components** — appshell_AppShell, appshell_AppShellLayout, sidebar_Sidebar, topbar_TopBar, navitem_NavItem [INFERRED 0.95]
- **TopBar Composed Components** — topbar_TopBar, searchbar_SearchBar, themetoggle_ThemeToggle, usermenu_UserMenu [EXTRACTED 1.00]
- **Media Preview Players** — filepreviewmodal_ImageViewer, filepreviewmodal_AudioPlayer, filepreviewmodal_VideoPlayer [INFERRED 0.95]
- **ShareDialog Internal Tabs** — sharedialog_ShareDialog, sharedialog_PublicLinkTab, sharedialog_AccessTab, sharedialog_UserCombobox [EXTRACTED 1.00]
- **Global Context Providers used in AppShell** — ctx_breadcrumb, ctx_upload, ctx_infoPanel, appshell_AppShell [EXTRACTED 1.00]
- **shadcn/ui Primitive Components** — ui_avatar_Avatar, ui_badge_Badge, ui_breadcrumb_Breadcrumb, ui_button_Button, ui_card_Card [INFERRED 0.95]
- **Radix UI Primitive Wrappers** — context_menu_ContextMenu, dialog_Dialog, dropdown_menu_DropdownMenu, label_Label, progress_Progress, separator_Separator, tooltip_Tooltip, sheet_Sheet [EXTRACTED 1.00]
- **shadcn/ui Component Library** — checkbox_Checkbox, context_menu_ContextMenu, dialog_Dialog, dropdown_menu_DropdownMenu, input_Input, label_Label, progress_Progress, separator_Separator, sheet_Sheet, skeleton_Skeleton, sonner_Toaster, tooltip_Tooltip [INFERRED 0.95]
- **React Context Providers** — auth_AuthProvider, breadcrumb_BreadcrumbProvider, infoPanel_InfoPanelProvider, upload_UploadProvider [EXTRACTED 1.00]
- **File Management Hooks** — useFileBrowser_useFileBrowser, useFolderDownload_useFolderDownload, useFolderUpload_useFolderUpload [INFERRED 0.85]
- **Multipart Upload Pipeline** — upload_UploadProvider, upload_reducer, upload_UploadTask, api_uploadsApi, useFolderUpload_useFolderUpload [EXTRACTED 1.00]
- **Folder Archive Download Pipeline** — useFolderDownload_useFolderDownload, api_nodesApi, api_foldersApi, api_tasksApi, api_downloadsApi [EXTRACTED 1.00]
- **Authentication Pages Group** — pages_Login_LoginPage, pages_Register_RegisterPage, pages_ForgotPassword_ForgotPasswordPage, pages_ResetPassword_ResetPasswordPage [INFERRED 0.95]
- **Admin Panel Pages Group** — admin_AdminLayout, admin_AuditPage, admin_QuotaRequestsPage, admin_RegistrationPage, admin_TasksPage, admin_UserDetailSheet, admin_UsersPage [EXTRACTED 0.95]
- **FilesPage Core Hooks** — pages_Files_FilesPage, hooks_useFileBrowser, hooks_useFolderUpload, useShareBadges_hook, useThumbnails_hook [INFERRED 0.75]
- **SharedRow Dialog Components** — pages_SharedWithMe_SharedRow, components_RenameDialog, components_MoveDialog, components_ShareDialog, components_DeleteConfirmDialog [EXTRACTED 0.95]
- **Auth Type Definitions** — types_auth_LoginRequest, types_auth_LoginResponse, types_auth_AuthSession, types_auth_PasswordResetRequest, types_auth_PasswordResetRequestResponse, types_auth_PasswordResetConfirmRequest, types_auth_RefreshResponse [EXTRACTED 0.95]
- **Common Pagination Types** — types_common_PageMeta, types_common_PageResponse, types_common_PaginationParams [EXTRACTED 0.95]
- **Admin User Management Features** — admin_UsersPage, admin_UserRow, admin_UserDetailSheet, api_users, api_quotas, api_audit [INFERRED 0.85]
- **Filesystem Node Type System** — nodes_NodeRead, nodes_NodeListItem, nodes_NodeType, nodes_NodeVisibility, nodes_NodeMoveRequest, nodes_NodeSearchResult [EXTRACTED 0.95]
- **File Management Type Group** — files_FileRead, files_FileListItem, files_FileDownloadRequest, files_FileDownloadResponse, files_FileRenameRequest, files_FileProcessingStatus, files_FilePreviewStatus, files_StorageObjectStatus [EXTRACTED 0.95]
- **Folder Management Type Group** — folders_FolderRead, folders_FolderCreateRequest, folders_FolderPatchRequest, folders_FolderArchiveResponse, folders_FolderContent [EXTRACTED 0.95]
- **Permission System Type Group** — permissions_PermissionGrantRequest, permissions_NodePermissionRead, permissions_NodePermissionListItem, permissions_PermissionRevokeRequest, permissions_PermissionLevel, permissions_PermissionSubjectType [EXTRACTED 0.95]
- **Public Link Type Group** — publiclinks_PublicLinkRead, publiclinks_PublicLinkListItem, publiclinks_PublicLinkCreateRequest, publiclinks_PublicLinkRevokeRequest, publiclinks_PublicLinkPublicRead, publiclinks_PublicLinkDownloadResponse, publiclinks_PublicLinkFolderArchiveResponse [EXTRACTED 0.95]
- **Upload Session Type Group** — uploads_UploadSessionRead, uploads_UploadSessionCreateRequest, uploads_PresignedPart, uploads_PresignedPartsResponse, uploads_UploadPartCompleteRequest, uploads_UploadCompletePart, uploads_UploadCompleteRequest, uploads_UploadCompleteResponse [EXTRACTED 0.95]
- **User Management Type Group** — users_CurrentUser, users_UserRead, users_UserListItem, users_RoleListItem, users_UserStatus [EXTRACTED 0.95]
- **Background Task Type Group** — tasks_BackgroundTask, tasks_BackgroundTaskListItem, tasks_BackgroundTaskStatus, tasks_BackgroundTaskType, tasks_TaskPriority [EXTRACTED 0.95]
- **Quota Management Type Group** — quotas_UserQuota, quotas_QuotaUsageRead, quotas_UserQuotaUpdate, quotas_QuotaIncreaseRequest, quotas_ServerStorage, quotas_QuotaIncreaseRequestStatus [EXTRACTED 0.95]
- **Registration Type Group** — registration_RegistrationRead, registration_RegistrationCreateRequest, registration_RegistrationApproveRequest, registration_RegistrationApproveResponse, registration_RegistrationRejectRequest, registration_RegistrationStatus [EXTRACTED 0.95]
- **All Frontend Types via Barrel Export** — index_TypesBarrel, files_FileRead, folders_FolderRead, nodes_NodeRead, uploads_UploadSessionRead, trash_TrashItemListItem, publiclinks_PublicLinkRead, permissions_NodePermissionRead, registration_RegistrationRead, tasks_BackgroundTask, users_CurrentUser, roles_Role, quotas_UserQuota [EXTRACTED 1.00]

## Communities (87 total, 44 thin omitted)

### Community 0 - "Quota Requests & Storage Admin"
Cohesion: 0.08
Nodes (46): STATUS_COLORS, STATUS_FILTER_OPTIONS, STATUS_LABELS, STATUS_COLORS, STATUS_FILTER_OPTIONS, STATUS_LABELS, authApi, quotasApi (+38 more)

### Community 1 - "Audit Log Viewer"
Cohesion: 0.06
Nodes (44): AuditPage(), RESULT_COLORS, RESULT_LABELS, RESULT_OPTIONS, auditApi, downloadsApi, filesApi, foldersApi (+36 more)

### Community 2 - "Node Sharing & Permissions API"
Cohesion: 0.06
Nodes (57): ShareBadge Interface, nodesApi, permissionsApi, trashApi, CreateFolderDialog Component, DeleteConfirmDialog Component, DropZone Component, FileActionBar Component (+49 more)

### Community 3 - "Admin Panel & Registration"
Cohesion: 0.06
Nodes (41): AdminLayout(), TABS, RegistrationPage(), STATUS_COLORS, STATUS_LABELS, STATUS_OPTIONS, TasksPage(), tasksApi (+33 more)

### Community 4 - "File Types & Preview"
Cohesion: 0.05
Nodes (50): FileListItem Interface, FilePreviewStatus Type, FileProcessingStatus Type, FileRead Interface, StorageObjectStatus Type, FolderArchiveResponse Interface, FolderContent Interface, FolderRead Interface (+42 more)

### Community 5 - "Error Boundary & UI Shell"
Cohesion: 0.06
Nodes (36): ErrorBoundary, Props, State, BreadcrumbContext, BreadcrumbContextValue, BreadcrumbItem, BreadcrumbProvider(), useBreadcrumb() (+28 more)

### Community 6 - "Admin Page Components"
Cohesion: 0.06
Nodes (43): AdminLayout Component, AuditPage Component, AuditRow Component, QuotaRequestsPage Component, RegistrationPage Component, ServerStorageCard Component, TasksPage Component, UserDetailSheet Component (+35 more)

### Community 7 - "Share Dialog & Permissions"
Cohesion: 0.09
Nodes (27): permissionsApi, publicLinksApi, PERM_FLAGS, PERM_LABELS, PermKey, Props, PublicLinkTab(), shareUrl() (+19 more)

### Community 8 - "File Action Bar & Info Panel"
Cohesion: 0.13
Nodes (22): useInfoPanel(), DeleteConfirmDialog(), FileActionBar(), Props, FolderColorDialog(), Props, MoveDialog(), RenameDialog() (+14 more)

### Community 9 - "Upload & Media Preview"
Cohesion: 0.10
Nodes (18): uploadsApi, formatTime(), PreviewKind, Props, SeekRow(), TEXT_APP_MIME, TEXT_EXTENSIONS, VideoPlayer() (+10 more)

### Community 10 - "Search & Debounce"
Cohesion: 0.11
Nodes (17): SearchBar(), useDebounce(), CYCLE, LABELS, ThemeToggle(), Breadcrumb, BreadcrumbItem, BreadcrumbLink (+9 more)

### Community 11 - "Node Info Panel & Quota Stats"
Cohesion: 0.13
Nodes (16): fmtDate(), Props, RESULT_COLORS, STATUS_COLORS, STATUS_LABELS, UserDetailSheet(), STATUS_COLORS, STATUS_LABELS (+8 more)

### Community 12 - "Build Config & Dependencies"
Cohesion: 0.09
Nodes (23): dependencies, axios, class-variance-authority, clsx, lucide-react, next-themes, @radix-ui/react-avatar, @radix-ui/react-context-menu (+15 more)

### Community 13 - "File Grid & Date Formatting"
Cohesion: 0.20
Nodes (16): SelectOpts, FileGridItem(), formatDate(), Props, FileIcon(), iconForMime(), Props, FileListItem() (+8 more)

### Community 14 - "Dev Dependencies & ESLint"
Cohesion: 0.10
Nodes (20): devDependencies, eslint, eslint-config-prettier, @eslint/js, eslint-plugin-react-hooks, eslint-plugin-react-refresh, globals, playwright (+12 more)

### Community 15 - "TypeScript Config"
Cohesion: 0.11
Nodes (19): compilerOptions, allowImportingTsExtensions, baseUrl, erasableSyntaxOnly, ignoreDeprecations, jsx, lib, module (+11 more)

### Community 16 - "Shadcn Component Config"
Cohesion: 0.11
Nodes (17): aliases, components, hooks, lib, ui, utils, iconLibrary, rsc (+9 more)

### Community 17 - "Auth Context & Public Links"
Cohesion: 0.16
Nodes (18): publicLinksApi, quotasApi, ChangePasswordDialog, Auth Context, Breadcrumb Context, useMyQuota hook, NavItem, RequestStorageDialog (+10 more)

### Community 18 - "TS Compiler Options"
Cohesion: 0.12
Nodes (16): compilerOptions, allowImportingTsExtensions, erasableSyntaxOnly, lib, module, moduleDetection, moduleResolution, noEmit (+8 more)

### Community 19 - "Quota Request Cards"
Cohesion: 0.20
Nodes (11): RequestRow(), ServerStorageCard(), formatBytes(), useMyQuota(), NavItem(), Props, Props, Sidebar() (+3 more)

### Community 20 - "UI Module 20"
Cohesion: 0.16
Nodes (14): downloadsApi, foldersApi, tasksApi, uploadsApi, Progress Component, @radix-ui/react-progress, Toaster (Sonner) Component, Upload Context (+6 more)

### Community 21 - "UI Module 21"
Cohesion: 0.19
Nodes (7): nodesApi, Semaphore, thumbnailSemaphore, NodeMoveRequest, NodeSearchResult, NodeType, NodeVisibility

### Community 22 - "UI Module 22"
Cohesion: 0.21
Nodes (10): InfoPanelContext, InfoPanelContextValue, Props, getFolderColor(), Props, formatDateFull(), NodeInfoPanel(), Props (+2 more)

### Community 23 - "UI Module 23"
Cohesion: 0.24
Nodes (12): nodesApi, AudioPlayer, FilePreviewModal, ImageViewer, VideoPlayer, detectPreviewKind, DeleteConfirmDialog, useFolderDownload hook (+4 more)

### Community 24 - "UI Module 24"
Cohesion: 0.23
Nodes (12): API Client (axios instance), rolesApi, tasksApi, trashApi, PageResponse Type, Role Type, BackgroundTask Types, Trash Types (+4 more)

### Community 25 - "UI Module 25"
Cohesion: 0.24
Nodes (11): auditApi - Audit Logs API, authApi - Authentication API, downloadsApi - Archive Downloads API, filesApi - Files API, foldersApi - Folders API, API Module Barrel Export, nodesApi - Nodes API, permissionsApi - Permissions API (+3 more)

### Community 26 - "UI Module 26"
Cohesion: 0.24
Nodes (8): ContextMenuCheckboxItem, ContextMenuContent, ContextMenuItem, ContextMenuLabel, ContextMenuRadioItem, ContextMenuSeparator, ContextMenuSubContent, ContextMenuSubTrigger

### Community 27 - "UI Module 27"
Cohesion: 0.27
Nodes (6): FileGrid(), Props, sortItems(), useShareBadges(), useThumbnails(), Skeleton()

### Community 28 - "UI Module 28"
Cohesion: 0.20
Nodes (6): include, files, include, references, Path Alias @/* -> src/*, Vite Dev Proxy to Backend (localhost:8000)

### Community 29 - "UI Module 29"
Cohesion: 0.22
Nodes (10): Breadcrumb Context, BreadcrumbProvider, useBreadcrumb Hook, InfoPanel Context, InfoPanelProvider, useInfoPanel Hook, FolderRead Type, NodeListItem Type (+2 more)

### Community 30 - "UI Module 30"
Cohesion: 0.20
Nodes (9): name, private, scripts, build, dev, lint, preview, type (+1 more)

### Community 31 - "UI Module 31"
Cohesion: 0.39
Nodes (9): Cyan Accent (#47bfff), Deep Purple Glow (#7e14ff), Lavender Highlight (#ede6ff), Primary Purple Color (#863bff), Blurred Ellipse Glow Effect (Gaussian Blur Filters), Lightning Bolt Shape (Primary Path), Favicon SVG Icon, Frontend Public Assets Directory (+1 more)

### Community 32 - "UI Module 32"
Cohesion: 0.33
Nodes (9): AppShell, AppShellLayout, InfoPanel Context, Upload Context, FileIcon, FolderColorDialog, NodeInfoPanel, TaskRow (+1 more)

### Community 33 - "UI Module 33"
Cohesion: 0.25
Nodes (8): App Root Component, AdminLayout Component, AppShell Layout Component, AuthProvider (context wrapper), ProtectedRoute Component, Application Entry Point, QueryClientProvider (TanStack Query), ThemeProvider

### Community 34 - "UI Module 34"
Cohesion: 0.71
Nodes (7): Bluesky Social Icon, Discord Social Icon, Documentation Icon, GitHub Social Icon, Social/User Profile Icon, icons.svg SVG Sprite Sheet, X (Twitter) Social Icon

### Community 35 - "UI Module 35"
Cohesion: 0.40
Nodes (5): compilerOptions, baseUrl, ignoreDeprecations, paths, @/*

### Community 36 - "UI Module 36"
Cohesion: 0.50
Nodes (5): Frontend Application, Purple Brand Color, Hero Image, Layered Platform / Cloud Stack Metaphor, Isometric Layered Design Style

### Community 37 - "UI Module 37"
Cohesion: 0.50
Nodes (5): authApi, Auth Context, AuthProvider, useAuth Hook, CurrentUser Type

### Community 38 - "UI Module 38"
Cohesion: 0.67
Nodes (4): permissionsApi, usersApi, AccessTab, UserCombobox

### Community 39 - "UI Module 39"
Cohesion: 0.50
Nodes (3): Avatar, AvatarFallback, AvatarImage

### Community 40 - "UI Module 40"
Cohesion: 0.67
Nodes (3): Badge(), BadgeProps, badgeVariants

### Community 41 - "UI Module 41"
Cohesion: 1.00
Nodes (3): Dialog Component Suite, @radix-ui/react-dialog, Sheet Component Suite

## Knowledge Gaps
- **354 isolated node(s):** `$schema`, `style`, `rsc`, `tsx`, `config` (+349 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **44 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `SharedRow Component` connect `Node Sharing & Permissions API` to `Admin Page Components`?**
  _High betweenness centrality (0.213) - this node is a cross-community bridge._
- **Why does `SharedWithMeItem Type` connect `Node Sharing & Permissions API` to `File Action Bar & Info Panel`?**
  _High betweenness centrality (0.199) - this node is a cross-community bridge._
- **What connects `$schema`, `style`, `rsc` to the rest of the system?**
  _357 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Quota Requests & Storage Admin` be split into smaller, more focused modules?**
  _Cohesion score 0.07997038134024435 - nodes in this community are weakly interconnected._
- **Should `Audit Log Viewer` be split into smaller, more focused modules?**
  _Cohesion score 0.05605499735589635 - nodes in this community are weakly interconnected._
- **Should `Node Sharing & Permissions API` be split into smaller, more focused modules?**
  _Cohesion score 0.06203007518796992 - nodes in this community are weakly interconnected._
- **Should `Admin Panel & Registration` be split into smaller, more focused modules?**
  _Cohesion score 0.05909090909090909 - nodes in this community are weakly interconnected._