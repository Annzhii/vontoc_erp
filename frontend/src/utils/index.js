export const getSidebarLinks = () => [
	{
		label: ('Inbox'),
		icon: 'Inbox',
		to: 'Inbox',
		activeFor: ['Inbox', 'InboxMail'],
	},
	{
		label: ('Sent'),
		icon: 'Send',
		to: 'Sent',
		activeFor: ['Sent', 'SentMail'],
	},
	{
		label: ('Outbox'),
		icon: 'MailQuestion',
		to: 'Outbox',
		activeFor: ['Outbox', 'OutboxMail'],
	},
	{
		label: ('Drafts'),
		icon: 'Edit3',
		to: 'Drafts',
		activeFor: ['Drafts', 'DraftsMail'],
	},
	{
		label: ('Spam'),
		icon: 'MailWarning',
		to: 'Spam',
		activeFor: ['Spam', 'SpamMail'],
	},
	{
		label: ('Trash'),
		icon: 'Trash2',
		to: 'Trash',
		activeFor: ['Trash', 'TrashMail'],
	},
	{
		label: ('Domains'),
		icon: 'Globe',
		to: 'Domains',
		activeFor: ['Domains', 'Domain'],
		forDashboard: true,
	},
	{
		label: ('Members'),
		icon: 'Users',
		to: 'Members',
		activeFor: ['Members', 'Invites'],
		forDashboard: true,
	},
	{
		label: ('Groups'),
		icon: 'Mails',
		to: 'Groups',
		activeFor: ['Groups', 'Group'],
		forDashboard: true,
	},
	{
		label: ('Aliases'),
		icon: 'AtSign',
		to: 'Aliases',
		activeFor: ['Aliases'],
		forDashboard: true,
	},
]

export const convertToTitleCase = (str) => 
	str?.toLowerCase()
	   .split(' ') 
	   .map(word => word.charAt(0).toUpperCase() + word.slice(1))
	   .join(' ') || '';
  

export const formatBytes = (bytes) => {
	if (!+bytes) return '0 Bytes' 

	const k = 1024
	const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']

	const i = Math.floor(Math.log(bytes) / Math.log(k))

	return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))}${sizes[i]}`
}

export const validateEmail = (email) => {
	const regExp =
		/^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
	return regExp.test(email)
}