import { reactive } from 'vue'
import { useRoute } from 'vue-router'
import { defineStore } from 'pinia'
import { createResource } from 'frappe-ui'

import router from '@/router'

export const userStore = defineStore('mail-users', () => {
	const route = useRoute()

	const userResource = createResource({
		url: '/api/method/vontoc_erp.api.account.get_user_info',
		onError: (error) => {
			if (error && error.exc_type === 'AuthenticationError') router.push('/login')
		},
		auto: true,
	})

	const getParsedItem = (key) => {
		const item = sessionStorage.getItem(key)
		return item ? JSON.parse(item) : null
	}

	const currentMail = reactive({
		Inbox: getParsedItem('currentInboxMail'),
		Sent: getParsedItem('currentSentMail'),
		Outbox: getParsedItem('currentOutboxMail'),
		Drafts: getParsedItem('currentDraftsMail'),
		Spam: getParsedItem('currentSpamMail'),
		Trash: getParsedItem('currentTrashMail'),
	})

	const setCurrentMail = (folder, mail) => {
		const itemName = `current${folder}Mail`
		if (mail) {
			currentMail[folder] = mail
			sessionStorage.setItem(itemName, JSON.stringify(mail))
			if (String(route.name).startsWith(folder))
				router.push({ name: `${folder}Mail`, params: { id: mail } })
		} else {
			currentMail[folder] = null
			sessionStorage.removeItem(itemName)
			router.push({ name: folder })
		}
	}

	return { userResource, currentMail, setCurrentMail }
})
