<template>
	<Button
		:icon-left="['Trash', 'Spam'].includes(currentFolder) ? 'trash-2' : 'edit'"
		@click="performAction"
	>
		{{ buttonMessage }}
	</Button>

	
	<Dialog v-model="showConfirmDialog" :options="confirmDialogOptions" />
</template>

<script setup>
import { computed, ref } from 'vue'
import { Button, Dialog, createResource } from 'frappe-ui'

// import SendMail from '@/components/SendMail.vue'

// 使用 defineProps 和 defineEmits（编译宏，JS 里不需要引入）
const { currentFolder } = defineProps()
const emit = defineEmits(['reloadMails'])

const showSendModal = ref(false)
const showConfirmDialog = ref(false)

const buttonMessage = computed(() => {
	if (currentFolder === 'Trash') return ('Empty Trash')
	if (currentFolder === 'Spam') return ('Empty Spam')
	return ('Compose')
})

const confirmDialogOptions = computed(() => ({
	title: `${buttonMessage.value}?`,
	message: ('This action cannot be undone.'),
	icon: { name: 'alert-triangle', appearance: 'warning' },
	actions: [
		{
			label: ('Confirm'),
			variant: 'solid',
			onClick: () => {
				emptyFolder.submit()
				showConfirmDialog.value = false
			},
		},
	],
}))

const performAction = () => {
	if (['Trash', 'Spam'].includes(currentFolder)) {
		showConfirmDialog.value = true
	} else {
		showSendModal.value = true
	}
}

const emptyFolder = createResource({
	url: 'mail.api.mail.empty_folder',
	makeParams: () => ({ folder: currentFolder }),
	onSuccess: () => emit('reloadMails'),
})
</script>
