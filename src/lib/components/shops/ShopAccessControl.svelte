<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	import { getGroups } from '$lib/apis/groups';
	import { getAllUsers } from '$lib/apis/users';
	import Badge from '$lib/components/common/Badge.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';

	export let accessControl: any = null;
	export let onChange: (accessControl: any) => void = () => {};

	let groups = [];
	let users = [];
	let selectedGroupId = '';
	let selectedUserId = '';
	let loading = true;

	const initAccessControl = () => {
		if (accessControl === null) {
			accessControl = {
				read: {
					group_ids: [],
					user_ids: []
				},
				write: {
					group_ids: [],
					user_ids: []
				}
			};
		} else {
			accessControl = {
				read: {
					group_ids: accessControl?.read?.group_ids ?? [],
					user_ids: accessControl?.read?.user_ids ?? []
				},
				write: {
					group_ids: accessControl?.write?.group_ids ?? [],
					user_ids: accessControl?.write?.user_ids ?? []
				}
			};
		}
		onChange(accessControl);
	};

	onMount(async () => {
		try {
			const [groupsResponse, usersResponse] = await Promise.all([
				getGroups(localStorage.token, true),
				getAllUsers(localStorage.token)
			]);
			
			// Ensure groups is an array
			if (Array.isArray(groupsResponse)) {
				groups = groupsResponse;
			} else if (groupsResponse && Array.isArray(groupsResponse.groups)) {
				groups = groupsResponse.groups;
			} else if (groupsResponse && Array.isArray(groupsResponse.items)) {
				groups = groupsResponse.items;
			} else {
				groups = [];
			}
			
			// Ensure users is an array
			if (Array.isArray(usersResponse)) {
				users = usersResponse;
			} else if (usersResponse && Array.isArray(usersResponse.users)) {
				users = usersResponse.users;
			} else if (usersResponse && Array.isArray(usersResponse.items)) {
				users = usersResponse.items;
			} else {
				users = [];
			}
			
			initAccessControl();
		} catch (error) {
			console.error('Error loading groups/users:', error);
			toast.error($i18n.t('Failed to load users and groups'));
			groups = [];
			users = [];
		} finally {
			loading = false;
		}
	});

	$: if (accessControl !== null && !loading) {
		// Ensure accessControl structure is correct when it changes
		if (!accessControl.read || !accessControl.write) {
			initAccessControl();
		}
	}

	const toggleGroupPermission = (groupId: string) => {
		if (!accessControl) return;
		
		const hasRead = (accessControl.read?.group_ids ?? []).includes(groupId);
		const hasWrite = (accessControl.write?.group_ids ?? []).includes(groupId);

		if (hasWrite) {
			// Remove from write, keep in read
			accessControl.write.group_ids = (accessControl.write?.group_ids ?? []).filter((id: string) => id !== groupId);
		} else if (hasRead) {
			// Upgrade to write
			accessControl.write.group_ids = [...(accessControl.write?.group_ids ?? []), groupId];
		} else {
			// Add to read
			accessControl.read.group_ids = [...(accessControl.read?.group_ids ?? []), groupId];
		}
		onChange(accessControl);
	};

	const removeGroup = (groupId: string) => {
		if (!accessControl) return;
		accessControl.read.group_ids = (accessControl.read?.group_ids ?? []).filter((id: string) => id !== groupId);
		accessControl.write.group_ids = (accessControl.write?.group_ids ?? []).filter((id: string) => id !== groupId);
		onChange(accessControl);
	};

	const toggleUserPermission = (userId: string) => {
		if (!accessControl) return;
		
		const hasRead = (accessControl.read?.user_ids ?? []).includes(userId);
		const hasWrite = (accessControl.write?.user_ids ?? []).includes(userId);

		if (hasWrite) {
			// Remove from write, keep in read
			accessControl.write.user_ids = (accessControl.write?.user_ids ?? []).filter((id: string) => id !== userId);
		} else if (hasRead) {
			// Upgrade to write
			accessControl.write.user_ids = [...(accessControl.write?.user_ids ?? []), userId];
		} else {
			// Add to read
			accessControl.read.user_ids = [...(accessControl.read?.user_ids ?? []), userId];
		}
		onChange(accessControl);
	};

	const removeUser = (userId: string) => {
		if (!accessControl) return;
		accessControl.read.user_ids = (accessControl.read?.user_ids ?? []).filter((id: string) => id !== userId);
		accessControl.write.user_ids = (accessControl.write?.user_ids ?? []).filter((id: string) => id !== userId);
		onChange(accessControl);
	};

	const addGroup = () => {
		if (selectedGroupId && accessControl) {
			if (!(accessControl.read?.group_ids ?? []).includes(selectedGroupId)) {
				accessControl.read.group_ids = [...(accessControl.read?.group_ids ?? []), selectedGroupId];
				onChange(accessControl);
			}
			selectedGroupId = '';
		}
	};

	const addUser = () => {
		if (selectedUserId && accessControl) {
			if (!(accessControl.read?.user_ids ?? []).includes(selectedUserId)) {
				accessControl.read.user_ids = [...(accessControl.read?.user_ids ?? []), selectedUserId];
				onChange(accessControl);
			}
			selectedUserId = '';
		}
	};

	$: accessGroups = Array.isArray(groups) ? groups.filter((group) =>
		(accessControl?.read?.group_ids ?? []).includes(group.id)
	) : [];

	$: accessUsers = Array.isArray(users) ? users.filter((user) =>
		(accessControl?.read?.user_ids ?? []).includes(user.id)
	) : [];

	$: availableGroups = Array.isArray(groups) ? groups.filter((group) =>
		!(accessControl?.read?.group_ids ?? []).includes(group.id)
	) : [];

	$: availableUsers = Array.isArray(users) ? users.filter((user) =>
		!(accessControl?.read?.user_ids ?? []).includes(user.id)
	) : [];
</script>

{#if loading}
	<div class="flex items-center justify-center py-4">
		<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Loading...')}</div>
	</div>
{:else if accessControl !== null}
	<div class="space-y-6">
		<!-- Groups Section -->
		<div>
			<div class="flex justify-between items-center mb-3">
				<div class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
					{$i18n.t('Groups')}
				</div>
			</div>

			{#if accessGroups.length > 0}
				<div class="space-y-2 mb-4">
					{#each accessGroups as group}
						<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<div class="flex items-center gap-2 flex-1">
								<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{group.name}
								</span>
								{#if group.member_count !== undefined}
									<span class="text-xs text-gray-500 dark:text-gray-400">
										({group.member_count} {$i18n.t('members')})
									</span>
								{/if}
							</div>
							<div class="flex items-center gap-2">
								<button
									type="button"
									on:click={() => toggleGroupPermission(group.id)}
									class="px-3 py-1 text-xs rounded-md transition-colors"
									class:bg-blue-100={!(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:text-blue-700={!(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:dark:bg-blue-900={!(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:dark:text-blue-300={!(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:bg-green-100={(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:text-green-700={(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:dark:bg-green-900={(accessControl?.write?.group_ids ?? []).includes(group.id)}
									class:dark:text-green-300={(accessControl?.write?.group_ids ?? []).includes(group.id)}
								>
									{#if (accessControl?.write?.group_ids ?? []).includes(group.id)}
										{$i18n.t('Write')}
									{:else}
										{$i18n.t('Read')}
									{/if}
								</button>
								<button
									type="button"
									on:click={() => removeGroup(group.id)}
									class="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
									title={$i18n.t('Remove')}
								>
									<XMark class="w-4 h-4 text-gray-500 dark:text-gray-400" />
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<div class="flex gap-2">
				<select
					bind:value={selectedGroupId}
					class="flex-1 px-3 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all"
				>
					<option value="">{$i18n.t('Select a group')}</option>
					{#each availableGroups as group}
						<option value={group.id}>{group.name}</option>
					{/each}
				</select>
				<button
					type="button"
					on:click={addGroup}
					disabled={!selectedGroupId}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
				>
					{$i18n.t('Add')}
				</button>
			</div>
		</div>

		<!-- Users Section -->
		<div>
			<div class="flex justify-between items-center mb-3">
				<div class="block text-sm font-semibold text-gray-700 dark:text-gray-300">
					{$i18n.t('Users')}
				</div>
			</div>

			{#if accessUsers.length > 0}
				<div class="space-y-2 mb-4">
					{#each accessUsers as user}
						<div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<div class="flex items-center gap-2 flex-1">
								<div class="w-8 h-8 rounded-full bg-gradient-to-r from-blue-500 to-orange-500 flex items-center justify-center text-white text-xs font-semibold">
									{(user.name || user.email || 'U').charAt(0).toUpperCase()}
								</div>
								<div class="flex flex-col">
									<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
										{user.name || user.email || user.id}
									</span>
									{#if user.name && user.email}
										<span class="text-xs text-gray-500 dark:text-gray-400">
											{user.email}
										</span>
									{/if}
								</div>
							</div>
							<div class="flex items-center gap-2">
								<button
									type="button"
									on:click={() => toggleUserPermission(user.id)}
									class="px-3 py-1 text-xs rounded-md transition-colors"
									class:bg-blue-100={!(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:text-blue-700={!(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:dark:bg-blue-900={!(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:dark:text-blue-300={!(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:bg-green-100={(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:text-green-700={(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:dark:bg-green-900={(accessControl?.write?.user_ids ?? []).includes(user.id)}
									class:dark:text-green-300={(accessControl?.write?.user_ids ?? []).includes(user.id)}
								>
									{#if (accessControl?.write?.user_ids ?? []).includes(user.id)}
										{$i18n.t('Write')}
									{:else}
										{$i18n.t('Read')}
									{/if}
								</button>
								<button
									type="button"
									on:click={() => removeUser(user.id)}
									class="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
									title={$i18n.t('Remove')}
								>
									<XMark class="w-4 h-4 text-gray-500 dark:text-gray-400" />
								</button>
							</div>
						</div>
					{/each}
				</div>
			{/if}

			<div class="flex gap-2">
				<select
					bind:value={selectedUserId}
					class="flex-1 px-3 py-2 border-2 border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100 text-sm focus:border-blue-500 dark:focus:border-blue-400 focus:ring-2 focus:ring-blue-200 dark:focus:ring-blue-800 transition-all"
				>
					<option value="">{$i18n.t('Select a user')}</option>
					{#each availableUsers as user}
						<option value={user.id}>
							{user.name || user.email || user.id}
							{#if user.name && user.email} ({user.email}){/if}
						</option>
					{/each}
				</select>
				<button
					type="button"
					on:click={addUser}
					disabled={!selectedUserId}
					class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
				>
					{$i18n.t('Add')}
				</button>
			</div>
		</div>
	</div>
{/if}
