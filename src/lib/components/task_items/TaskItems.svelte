<script lang="ts">
	import { toast } from 'svelte-sonner';

	import dayjs from '$lib/dayjs';
	import duration from 'dayjs/plugin/duration';
	import relativeTime from 'dayjs/plugin/relativeTime';

	dayjs.extend(duration);
	dayjs.extend(relativeTime);

	async function loadLocale(locales) {
		for (const locale of locales) {
			try {
				dayjs.locale(locale);
				break;
			} catch (error) {
				console.error(`Could not load locale '${locale}':`, error);
			}
		}
	}

	import { onMount, getContext, onDestroy } from 'svelte';

	const i18n = getContext('i18n');
	$: loadLocale($i18n.languages);

	import { goto } from '$app/navigation';
	import { WEBUI_NAME, config, user } from '$lib/stores';
	import {
		createNewTaskItem,
		deleteTaskItemById,
		getTaskItemList,
		searchTaskItems,
		updateTaskItemById
	} from '$lib/apis/task_items';
	import { capitalizeFirstLetter, getTimeRange } from '$lib/utils';

	import EllipsisHorizontal from '../icons/EllipsisHorizontal.svelte';
	import DeleteConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Search from '../icons/Search.svelte';
	import Plus from '../icons/Plus.svelte';
	import Spinner from '../common/Spinner.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import FilesOverlay from '../chat/MessageInput/FilesOverlay.svelte';
	import XMark from '../icons/XMark.svelte';
	import DropdownOptions from '../common/DropdownOptions.svelte';
	import CheckCircle from '../icons/CheckCircle.svelte';
	import CheckCircleSolid from '../icons/CheckCircleSolid.svelte';

	let loaded = false;

	let selectedTaskItem = null;
	let showDeleteConfirm = false;

	let items = null;
	let total = null;

	let query = '';

	let sortKey = null;
	let viewOption = null;
	let permission = null;
	let completedFilter: boolean | null = null;

	let page = 1;

	let itemsLoading = false;
	let allItemsLoaded = false;

	const deleteTaskItemHandler = async (id) => {
		const res = await deleteTaskItemById(localStorage.token, id).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		if (res) {
			init();
		}
	};

	const toggleTaskItemCompleted = async (taskItem) => {
		await updateTaskItemById(localStorage.token, taskItem.id, {
			title: taskItem.title,
			description: taskItem.description,
			completed: !taskItem.completed,
			data: taskItem.data,
			meta: taskItem.meta,
			access_control: taskItem.access_control
		}).catch((error) => {
			toast.error(`${error}`);
		});
		init();
	};

	const reset = () => {
		page = 1;
		items = null;
		total = null;
		allItemsLoaded = false;
		itemsLoading = false;
	};

	const loadMoreItems = async () => {
		if (allItemsLoaded) return;
		page += 1;
		await getItemsPage();
	};

	const init = async () => {
		reset();
		await getItemsPage();
	};

	$: if (
		loaded &&
		query !== undefined &&
		sortKey !== undefined &&
		permission !== undefined &&
		viewOption !== undefined &&
		completedFilter !== undefined
	) {
		init();
	}

	const getItemsPage = async () => {
		itemsLoading = true;

		if (viewOption === 'created') {
			permission = null;
		}

		const res = await searchTaskItems(
			localStorage.token,
			query,
			viewOption,
			permission,
			completedFilter,
			sortKey,
			page
		).catch(() => {
			return [];
		});

		if (res) {
			total = res.total;
			const pageItems = res.items;

			if ((pageItems ?? []).length === 0) {
				allItemsLoaded = true;
			} else {
				allItemsLoaded = false;
			}

			if (items) {
				items = [...items, ...pageItems];
			} else {
				items = pageItems;
			}
		}

		itemsLoading = false;
		return res;
	};

	const groupTaskItems = (res) => {
		if (!Array.isArray(res)) {
			return [];
		}

		const grouped: Record<string, any[]> = {};
		const orderedKeys: string[] = [];

		for (const taskItem of res) {
			const timeRange = getTimeRange(taskItem.updated_at / 1000000000);
			if (!grouped[timeRange]) {
				grouped[timeRange] = [];
				orderedKeys.push(timeRange);
			}
			grouped[timeRange].push({
				...taskItem,
				timeRange
			});
		}

		return orderedKeys.map((key) => [key, grouped[key]] as [string, any[]]);
	};

	onMount(async () => {
		viewOption = localStorage?.taskItemViewOption ?? null;
		completedFilter = localStorage?.taskItemCompletedFilter ?? null;

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Tasks')} • {$WEBUI_NAME}
	</title>
</svelte:head>

<div id="task-items-container" class="w-full min-h-full h-full px-3 md:px-[18px]">
	{#if loaded}
		<DeleteConfirmDialog
			bind:show={showDeleteConfirm}
			title={$i18n.t('Delete task?')}
			on:confirm={() => {
				deleteTaskItemHandler(selectedTaskItem.id);
				showDeleteConfirm = false;
			}}
		>
			<div class=" text-sm text-gray-500 truncate">
				{$i18n.t('This will delete')} <span class="  font-semibold">{selectedTaskItem.title}</span>.
			</div>
		</DeleteConfirmDialog>

		<div class="flex flex-col gap-1 px-1 mt-1.5 mb-3">
			<div class="flex justify-between items-center">
				<div class="flex items-center md:self-center text-xl font-medium px-0.5 gap-2 shrink-0">
					<div>
						{$i18n.t('Tasks')}
					</div>

					<div class="text-lg font-medium text-gray-500 dark:text-gray-500">
						{total}
					</div>
				</div>

				<div class="flex w-full justify-end gap-1.5">
					<button
						class=" px-2 py-1.5 rounded-xl bg-black text-white dark:bg-white dark:text-black transition font-medium text-sm flex items-center"
						on:click={async () => {
							const res = await createNewTaskItem(localStorage.token, {
								title: $i18n.t('New Task'),
								description: '',
								completed: false,
								data: null,
								meta: null,
								access_control: {}
							}).catch((error) => {
								toast.error(`${error}`);
								return null;
							});

							if (res) {
								goto(`/task_items/${res.id}`);
							}
						}}
					>
						<Plus className="size-3" strokeWidth="2.5" />

						<div class=" ml-1 text-xs">{$i18n.t('New Task')}</div>
					</button>
				</div>
			</div>
		</div>

		<div
			class="py-2 bg-white dark:bg-gray-900 rounded-3xl border border-gray-100/30 dark:border-gray-850/30"
		>
			<div class="px-3.5 flex flex-1 items-center w-full space-x-2 py-0.5 pb-2">
				<div class="flex flex-1 items-center">
					<div class=" self-center ml-1 mr-3">
						<Search className="size-3.5" />
					</div>
					<input
						class=" w-full text-sm py-1 rounded-r-xl outline-hidden bg-transparent"
						bind:value={query}
						placeholder={$i18n.t('Search Tasks')}
					/>

					{#if query}
						<div class="self-center pl-1.5 translate-y-[0.5px] rounded-l-xl bg-transparent">
							<button
								class="p-0.5 rounded-full hover:bg-gray-100 dark:hover:bg-gray-900 transition"
								on:click={() => {
									query = '';
								}}
							>
								<XMark className="size-3" strokeWidth="2" />
							</button>
						</div>
					{/if}
				</div>
			</div>

			<div class="px-3 flex justify-between">
				<div
					class="flex w-full bg-transparent overflow-x-auto scrollbar-none"
					on:wheel={(e) => {
						if (e.deltaY !== 0) {
							e.preventDefault();
							e.currentTarget.scrollLeft += e.deltaY;
						}
					}}
				>
					<div
						class="flex gap-3 w-fit text-center text-sm rounded-full bg-transparent px-0.5 whitespace-nowrap"
					>
						<DropdownOptions
							align="start"
							className="flex w-full items-center gap-2 truncate px-3 py-1.5 text-sm bg-gray-50 dark:bg-gray-850 rounded-xl  placeholder-gray-400 outline-hidden focus:outline-hidden"
							bind:value={viewOption}
							items={[
								{ value: null, label: $i18n.t('All') },
								{ value: 'created', label: $i18n.t('Created by you') },
								{ value: 'shared', label: $i18n.t('Shared with you') }
							]}
							onChange={(value) => {
								if (value) {
									localStorage.taskItemViewOption = value;
								} else {
									delete localStorage.taskItemViewOption;
								}
							}}
						/>

						{#if [null, 'shared'].includes(viewOption)}
							<DropdownOptions
								align="start"
								bind:value={permission}
								items={[
									{ value: null, label: $i18n.t('Write') },
									{ value: 'read_only', label: $i18n.t('Read Only') }
								]}
							/>
						{/if}

						<DropdownOptions
							align="start"
							bind:value={completedFilter}
							items={[
								{ value: null, label: $i18n.t('All') },
								{ value: false, label: $i18n.t('Pending') },
								{ value: true, label: $i18n.t('Completed') }
							]}
							onChange={(value) => {
								if (value !== null) {
									localStorage.taskItemCompletedFilter = value;
								} else {
									delete localStorage.taskItemCompletedFilter;
								}
							}}
						/>
					</div>
				</div>
			</div>

			{#if items !== null && total !== null}
				{#if (items ?? []).length > 0}
					{@const groupedTaskItems = groupTaskItems(items)}

					<div class="@container h-full py-2.5 px-2.5">
						<div class="">
							{#each groupedTaskItems as [timeRange, taskItemsList], idx}
								<div
									class="w-full text-xs text-gray-500 dark:text-gray-500 font-medium px-2.5 pb-2.5"
								>
									{$i18n.t(timeRange)}
								</div>

								<div
									class="{groupedTaskItems.length - 1 !== idx ? 'mb-3' : ''} gap-1.5 flex flex-col"
								>
									{#each taskItemsList as taskItem, idx (taskItem.id)}
										<div
											class=" flex cursor-pointer w-full px-3.5 py-1.5 border border-gray-50 dark:border-gray-850/30 bg-transparent dark:hover:bg-gray-850 hover:bg-white rounded-2xl transition"
										>
											<div class="w-full flex items-center gap-3">
												<button
													class="flex-shrink-0"
													on:click|stopPropagation={() => {
														toggleTaskItemCompleted(taskItem);
													}}
												>
													{#if taskItem.completed}
														<CheckCircleSolid className="size-5 text-green-500" />
													{:else}
														<CheckCircle className="size-5 text-gray-400" />
													{/if}
												</button>

												<a href={`/task_items/${taskItem.id}`} class="flex-1 flex flex-col justify-between">
													<div class="flex-1">
														<div class="  flex items-center gap-2 self-center justify-between">
															<Tooltip
																content={taskItem.title}
																className="flex-1"
																placement="top-start"
															>
																<div
																	class=" text-sm font-medium capitalize flex-1 w-full line-clamp-1 {taskItem.completed
																		? 'line-through text-gray-400'
																		: ''}"
																>
																	{taskItem.title}
																</div>
															</Tooltip>

															<div class="flex shrink-0 items-center text-xs gap-2.5">
																<Tooltip
																	content={dayjs(taskItem.updated_at / 1000000).format('LLLL')}
																>
																	<div>
																		{dayjs(taskItem.updated_at / 1000000).fromNow()}
																	</div>
																</Tooltip>
																<Tooltip
																	content={taskItem?.user?.email ?? $i18n.t('Deleted User')}
																	className="flex shrink-0"
																	placement="top-start"
																>
																	<div class="shrink-0 text-gray-500">
																		{$i18n.t('By {{name}}', {
																			name: capitalizeFirstLetter(
																				taskItem?.user?.name ??
																					taskItem?.user?.email ??
																					$i18n.t('Deleted User')
																			)
																		})}
																	</div>
																</Tooltip>
															</div>
														</div>

														{#if taskItem.description}
															<div
																class=" text-xs text-gray-500 dark:text-gray-500 line-clamp-1 mt-0.5 {taskItem.completed
																	? 'line-through'
																	: ''}"
															>
																{taskItem.description}
															</div>
														{/if}
													</div>
												</a>

												<div class="flex shrink-0 items-center gap-1">
													<Tooltip content={$i18n.t('Options')}>
														<button
															class="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
															on:click|stopPropagation={(e) => {
																selectedTaskItem = taskItem;
																showDeleteConfirm = true;
															}}
														>
															<EllipsisHorizontal class="w-5 h-5 text-gray-600 dark:text-gray-300" />
														</button>
													</Tooltip>
												</div>
											</div>
										</div>
									{/each}
								</div>
							{/each}
						</div>

						{#if !allItemsLoaded}
							<div class="flex justify-center py-4">
								<button
									class="px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-800 text-sm font-medium hover:bg-gray-200 dark:hover:bg-gray-700 transition"
									on:click={loadMoreItems}
									disabled={itemsLoading}
								>
									{#if itemsLoading}
										<Spinner />
									{:else}
										{$i18n.t('Load More')}
									{/if}
								</button>
							</div>
						{/if}
					</div>
				{:else}
					<div class="flex flex-col items-center justify-center py-12">
						<div class="text-gray-500 dark:text-gray-400 text-sm">
							{$i18n.t('No tasks found')}
						</div>
					</div>
				{/if}
			{:else}
				<div class="flex justify-center py-12">
					<Spinner />
				</div>
			{/if}
		</div>
	{/if}
</div>
