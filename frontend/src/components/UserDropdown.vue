<template>
	<div>
		<Dropdown :options="userDropdownOptions">
			<template #default="{ open }">
				<button
					class="flex h-12 items-center rounded-md py-2 duration-300 ease-in-out"
					:class="
						isCollapsed
							? 'w-auto px-0'
							: open
								? 'w-52 bg-white px-2 shadow-sm'
								: 'w-52 px-2 hover:bg-gray-200'
					"
				>
					<span
						v-if="branding.data?.brand_html"
						class="h-8 w-8 flex-shrink-0 rounded"
						v-html="branding.data?.brand_html"
					></span>
					<maillogo v-else class="h-8 w-8 flex-shrink-0 rounded" />
					<div
						class="flex flex-1 flex-col text-left duration-300 ease-in-out"
						:class="
							isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<div class="text-base font-medium leading-none">
							<span
								v-if="
									branding.data?.brand_name &&
									branding.data?.brand_name != 'Frappe'
								"
							>
								{{ branding.data?.brand_name }}
							</span>
							<span v-else> Mail </span>
						</div>
						<div v-if="userResource" class="mt-1 text-sm leading-none text-gray-700">
							{{ convertToTitleCase(userResource.data?.full_name) }}
						</div>
					</div>
					<div
						class="duration-300 ease-in-out"
						:class="
							isCollapsed
								? 'ml-0 w-0 overflow-hidden opacity-0'
								: 'ml-2 w-auto opacity-100'
						"
					>
						<ChevronDown class="h-4 w-4 text-gray-700" />
					</div>
				</button>
			</template>
		</Dropdown>
		<SettingsModal v-model="showSettings" />
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronDown, Crown, LogOut, Mailbox, Settings as SettingsIcon } from 'lucide-vue-next'
import { Dropdown } from 'frappe-ui'

import { convertToTitleCase } from '@/utils'
import { sessionStore } from '@/stores/session'
import { userStore } from '@/stores/user'
import AppsMenu from '@/components//AppsMenu.vue'
import maillogo from '@/components/Icons/maillogo.vue'
//import SettingsModal from '@/components/Modals/SettingsModal.vue'

const { logout } = sessionStore()
const branding = {data: {
	"brand_name": "vontoc_erp",
	"brand_html": "",
	"favicon": "",
} }
// 注释动态获取用户信息，用于测试
//  const { userResource } = userStore()
const userResource = { data: {
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
const route = useRoute()
const router = useRouter()

const showSettings = ref(false)

defineProps<{ isCollapsed?: boolean }>()

const userDropdownOptions = [
	{
		icon: Mailbox,
		label: ('Mailbox'),
		onClick: () => router.push('/'),
		condition: () =>
			userResource.data.is_mail_admin &&
			userResource.data.default_outgoing &&
			route.meta.isDashboard,
	},
	{
		icon: Crown,
		label: ('Admin Dashboard'),
		onClick: () => router.push('/dashboard'),
		condition: () =>
			userResource.data.is_mail_admin &&
			userResource.data.default_outgoing &&
			!route.meta.isDashboard,
	},
	{
		icon: SettingsIcon,
		label: ('Settings'),
		onClick: () => {
			showSettings.value = true
		},
		condition: () => !userResource.data.is_tenant_owner,
	},
	{
		component: AppsMenu,
		condition: () => {
			const cookies = new URLSearchParams(document.cookie.split('; ').join('&'))
			return cookies.get('system_user') === 'yes'
		},
	},
	{
		icon: LogOut,
		label: ('Log Out'),
		onClick: logout.submit,
	},
]
</script>
