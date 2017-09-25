import logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

_eventQueue = []
_eventHandlers = {}

_postEventQueue = []

def queueEvent(eventType, **args):
	global _eventQueue
	logger.info('queueEvent: %s' % eventType)
	_eventQueue.append((eventType, args))

def queuePostEvent(eventType, **args):
	global _postEventQueue
	logger.info('queuePostEvent: %s' % eventType)
	_postEventQueue.append((eventType, args))

def registerHandler(handler, eventType):
	global _eventHandlers
	handlers = _eventHandlers.get(eventType)
	if handlers is None:
		handlers = {}

	key = (id(handler))
	handlers[key] = handler
	_eventHandlers[eventType] = handlers

def getRegisteredHandlers(eventType):
	global _eventHandlers
	if eventType not in _eventHandlers: return {}
	return _eventHandlers[eventType]

def __processHandler(eventType, args):
	logger.info('Process event: %s' % eventType)
	# Check if any handlers have been registered for this type of event
	handlers = _eventHandlers.get(eventType)
	if handlers is None:
		logger.warning('No handlers found for event: %s' % eventType)
		return

	for handlerId, handler in handlers.iteritems():
		handler(**args)

def processEvents():
	# Go through all the queued events and call respective registered handlers
	global _eventQueue, _postEventQueue, _eventHandlers
	for eventType, args in _eventQueue:
		__processHandler(eventType, args)

	for eventType, args in _postEventQueue:
		__processHandler(eventType, args)

	_eventQueue, _postEventQueue = [], []
