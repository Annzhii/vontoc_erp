<template>
	<header
		class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-3 py-2.5 sm:px-5"
	>
		<Breadcrumbs>
      <div>{{ currentFolder }}</div>
		</Breadcrumbs>
		<HeaderActions :current-folder="currentFolder" @reload-mails="reloadMails" />
	</header>
	<div class="relative flex h-[calc(100dvh-6rem)] sm:h-[calc(100dvh-3.05rem)]">
		<template v-if="mails[currentFolder].data?.length">
			<div
				ref="mailSidebar"
				class="sticky top-16 flex flex-col border-r"
				:class="!isMobile && userLayout === 'split' ? 'w-1/3' : 'w-full'"
			>
				<div class="flex items-center justify-between border-b px-3.5 py-2.5 sm:px-5">
					<div class="text-base">
						<span v-if="selections.length">{{
							('{0} {1} selected', [
								String(selections.length),
								selections.length === 1 ? 'item' : 'items',
							])
						}}</span>
						<span v-else>{{ ('All Mail') }}</span>
					</div>
					<div class="flex items-center space-x-1.5 sm:space-x-3">
						<Tooltip
							v-if="!isMobile && !selections.length"
							:text="('Select Layout')"
						>
							<Dropdown
								:options="[
									{
										label: ('Full Width'),
										icon: Rows4,
										onClick: () => setUserLayout('full'),
									},
									{
										label: ('Vertical Split'),
										icon: PanelLeft,
										onClick: () => setUserLayout('split'),
									},
								]"
							>
								<Button variant="ghost">
									<template #icon>
										<component
											:is="userLayout === 'full' ? Rows4 : PanelLeft"
											class="h-4 w-4 text-gray-600"
										/>
									</template>
								</Button>
							</Dropdown>
						</Tooltip>
						<Tooltip
							v-for="action in selectActions"
							:key="action.label"
							:text="action.label"
						>
							<Button variant="ghost" @click="action.onClick">
								<template #icon>
									<component :is="action.icon" class="h-4 w-4 text-gray-600" />
								</template>
							</Button>
						</Tooltip>
						<div class="flex items-center border-l pl-3.5 sm:pl-5">
							<Tooltip :text="('Select All')">
								<Checkbox
									v-model="allSelected"
									@change="allSelectedManuallyToggled = true"
								/>
							</Tooltip>
						</div>
					</div>
				</div>
				<div class="h-full overflow-y-auto overscroll-contain" @scroll="loadMoreEmails">
					<MailListItem
						v-for="(mail, idx) in mails[currentFolder].data"
						ref="mailItems"
						:key="idx"
						:mail
						:user-layout
						:class="{ 'bg-gray-50': mail.name == currentMail[currentFolder] }"
						@click="openMail(mail)"
						@select-mail="selectMail({ name: mail.name, mail_type: mail.mail_type })"
						@deselect-mail="deselectMail(mail.name)"
					/>
				</div>
			</div>
			<div class="flex cursor-col-resize justify-center" @mousedown="startResizing">
				<div
					ref="resizer"
					class="h-full rounded-full transition-all duration-300 ease-in-out group-hover:bg-gray-400"
				/>
			</div>
			<div
				class="overflow-y-auto bg-white"
				:class="{
					'w-2/3': !isMobile && userLayout === 'split',
					'absolute bottom-0 left-0 right-0 top-0 z-10':
						!isMobile && userLayout === 'full',
					'fixed inset-0 z-10': isMobile,
					hidden:
						(isMobile || userLayout === 'full') &&
						!(currentMail[currentFolder] || route.params.id),
				}"
			>
				<MailThread
					ref="mailThread"
					:mail-i-d="currentMail[currentFolder]"
					:current-folder
					:type="getMailType() || doctype"
					@reload-mails="reloadMails"
					@mark-as-unread="
						setSeen.submit({
							mails: [
								{ name: currentMail[currentFolder], mail_type: getMailType() },
							],
							seen: 0,
						})
					"
					@set-thread-folders="
						(move_to_trash) =>
							setFolderForThreads.submit({
								threads: [
									{ name: currentMail[currentFolder], mail_type: getMailType() },
								],
								move_to_trash,
							})
					"
					@delete-thread="
						deleteThreads.submit([
							{ name: currentMail[currentFolder], mail_type: getMailType() },
						])
					"
				/>
			</div>
		</template>
		<div v-else class="flex w-full flex-col items-center justify-center">
			<NoMails class="mb-2 h-16 w-16" />
			<p class="text-gray-500">
				{{ ('You have no mails in this folder.') }}
			</p>
		</div>
	</div>
</template>

<script setup>
import {
	Dropdown,
	Tooltip,
	createListResource,
	createResource,
} from 'frappe-ui'
import { computed, ref, inject } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import HeaderActions from '@/components/HeaderActions.vue'

const route = useRoute()
const showDialog = ref(false)

const currentFolder = computed(() => {
	const name = String(route.name)
  	return name.endsWith('frontend') ? name.replace('frontend', '') : name;
})

const folders = ['Inbox', 'Sent', 'Outbox', 'Drafts', 'Spam', 'Trash']

const doctype = "Communication"
//user 测试数据用于开发
const user = { data: {
  "message": {
    "name": "Administrator",
    "email": "admin@example.com",
    "enabled": 1,
    "user_image": null,
    "full_name": "Administrator",
    "first_name": "Administrator",
    "last_name": null,
    "user_type": "System User",
    "username": "administrator",
    "api_key": null,
    "roles": [
      "Mail Admin",
      "Mail User",
      "Raven Admin",
      "Raven User",
      "Analytics",
      "Supplier",
      "Agriculture Manager",
      "Agriculture User",
      "Support Team",
      "Quality Manager",
      "Fulfillment User",
      "Academics User",
      "Delivery User",
      "Fleet Manager",
      "Delivery Manager",
      "Customer",
      "Item Manager",
      "HR User",
      "Manufacturing User",
      "Projects Manager",
      "Projects User",
      "Manufacturing Manager",
      "HR Manager",
      "Stock Manager",
      "Stock User",
      "Employee",
      "Auditor",
      "Translator",
      "Sales Master Manager",
      "Maintenance Manager",
      "Purchase Master Manager",
      "Purchase Manager",
      "Sales Manager",
      "Maintenance User",
      "Purchase User",
      "Accounts Manager",
      "Accounts User",
      "Sales User",
      "Newsletter Manager",
      "Knowledge Base Editor",
      "Knowledge Base Contributor",
      "Blogger",
      "Marketing Manager",
      "Inbox User",
      "Prepared Report User",
      "Script Manager",
      "Report Manager",
      "Workspace Manager",
      "Dashboard Manager",
      "Website Manager",
      "System Manager",
      "Administrator",
      "Guest",
      "All",
      "Desk User"
    ],
    "is_mail_user": true,
    "is_mail_admin": true,
    "default_outgoing": "annnzhiii@gmail.com"
  }
}}

const createMailResource = (folder) =>
	createListResource({
		url: `vontoc_erp.api.mail.get_${folder.toLowerCase()}_mails`,
		doctype: doctype,
		pageLength: 50,
		cache: [`${folder}Mails`, user.data?.name],
		onSuccess: (data) => {
			const mailExists = (id) => data.some((m) => m.name === id)

			if (mailExists(id)) {
				if (currentMail[folder] !== id) setCurrentMail(folder, id ?? null)
				mailThread.value?.reload()
			} else if (mailExists(currentMail[folder])) {
				if (route.params.id !== currentMail[folder])
					router.replace({ name: `${folder}Mail`, params: { id: currentMail[folder] } })
				mailThread.value?.reload()
			} else setCurrentMail(folder, null)
		},
	})

const mails = Object.fromEntries(folders.map((folder) => [folder, createMailResource(folder)]))
console.log('邮件:', mails["Sent"].data)
console.log('邮件:', mails)
</script>
