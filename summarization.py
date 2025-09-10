import spacy
import speech_to_text as stt 

def summarize_meeting(transcript):

    """
        Testing for spaCy implementation of summary aspect
    """

    ACTION_VERBS = ["schedule", "finalize", "collaborate", "discuss", "present", "review", "follow", "send", "work"]
    trigger_words = {}

    if type(transcript) is list:
        transcript = ''.join((item for item in transcript))

    # Stripping ' and \n from transcription (seems slow with if statement above idk why)
    transcript = transcript.replace("\n"," ")

    nlp = spacy.load('en_core_web_md')
    
    doc = nlp(transcript)

    ents = []

    for sentence in doc.sents:
        lemmas = {token.lemma_.lower() for token in sentence if token.pos_ == "VERB"}

        # for token in sentence: 
        #     if token.lemma_.lower() in ACTION_VERBS and token.pos_ == "VERB":
        #         obj = " ".join(child.text for child in token.subtree)
        #         print(f"Action: {token.lemma_} -> Object: {obj}")

        intersection = lemmas.intersection(ACTION_VERBS)

        if intersection:
            
            for word in intersection:
                trigger_words[word] = sentence.text.strip()


    for poi in trigger_words.keys():
        print(f"{poi.upper()}: {trigger_words[poi]}")
    
        

if __name__ == "__main__":
#     summarize_meeting("""Let's start by scheduling the client meeting for Tuesday.
# Tom, please send the updated contract to Legal.
# We agreed that Vendor A is too expensive and we'll go with Vendor B instead.
# Make sure to follow-up with Finance about the Q4 report.
# """)
    # summarize_meeting(['The', 'man', 'came'])

    summarize_meeting("""
Some of the infrastructure improvements on the product side. I'm just not quite sure whose responsibility it is to focus on getting a handle on some of the constraints we have in replication. 
                      Yeah, what I was mentioning in the product key review about an hour ago, I think is sort of unrelated. And so I think the DRI needs to be your kind of data engineering team. 
                      But of course, there's a dependency on infrastructure because that's where the data is being piped from.
                       They do own that data source. Yeah, I'll say for the replication lag on that slave host where I'm sorry, not on the secondary host where the data is being pulled from, like the infrastructure would be the DRI for that.
                       And so any escalations, I'll own those. And I know we have an action plan for that as far as creating another dedicated host just for the data team to pull from. Okay. I did actually, I saw that issue. 
                      And I did talk to Craig Gomes a little bit as well on the database side, just to see if there's some database improvements. And I'm still trying to figure out if it's truly just dedicated computational sort of resource, a server, or if there's actually some database tuning that needs to occur. 
                      Do you have a sense of that? So I'd say it's three different things. It's having a dedicated host that doesn't have conflicting query traffic coming from other workloads. There are some tuning performance or tuning improvements to be made. 
                      And then there's also improvements in, and this is where it does maybe relate a little bit to what the topic was in the last review, basically the overall demand on the database layer from .com activities and improving those. So it's definitely not just one of those things. 
                      One of the most specific actions we're going to take though is separating out and having a dedicated host so that we're just dealing with the profile of the data engineering traffic on there and not having conflicting queries affect the ability to update the replication. 
                      Steve, I definitely want to partner with you on this one because I think the demand on those databases is only going to increase. It's not going down. And I think we need to get, I'm still unclear on where to focus and to get the biggest bang for the buck. 
                      I think of the computational resource dedication, that's going to be a good thing, but I'm probably going to squeeze the balloon and then the next area will unearth itself. Okay, I'll tell you what I'll put into the InfraKey review for next week. Okay. 
                      An update on this issue. Thank you, Steve. So then back to Mac on seven or yes. Thank you. And Rob was in the SAS incident this morning as well. Brian, we have the attention there. 
                      Number seven, just to provide an update on previous conversations, we're continuing to improve defect tracking and against SLOs. There is a first iteration PI that we are experimenting to show percentage of defects meeting the SLOs. 
                      Key findings, S1s are hovering at 80% as two at 60. We've been focused mostly on S1, S2 at this point, hence why S3 and S4s are lower. And this will likely be the case. We are also in point B are working on the measurement for average open bugs age. This will give us a whole picture of what's left. If the age goes up or down, we are cleaning the backlog. The average age should go down as well. 
                      There's no PI yet, but I just want to update and show that beyond this, it's not off track. Number C, Craig, on S2? Yeah, I just was looking through the charts and I noted that there was a spike in mean time to close and just wanted to see if you had any insight into that. This is the S2s. The S1s looked fine. Yeah, this is where the point B on age and supplement those charts in the back end helps. So I haven't seen a dip in age, nor the count overall. I think it's the latter. We need to dig in a bit deeper in that. And also the data lag, I would like to reevaluate when we have the whole picture, when everything is synced in as well. Christy, you have some insights. Yeah, I'm just wondering if part of this could be the fact that we changed the severity across the board for MRs to S2. And so we may have some older bugs in there that hadn't been addressed because they were at a lower severity. 
                      Now we've moved them to S2 and maybe that caused a little spike. That could be the case. We did it in a limited fashion. It won't be a huge volume. We also iterated after that to pin on priority since product owns prioritization. So I wouldn't account it entirely to that. I mean, this isn't the infra key review, but I know that they've gotten backed up on those issues. So if some good portion of those are infra created or related, then that may be lifting it as well. I can take the deeper dig in and then provide an update next time. I think we need extra debug slicing of the data here. So you would like to go to point eight? Yeah, we are now measuring S1, S2, SLO achievement with closed bugs. But if you then look at the number of bugs, it's exponential growth. And then it would be trivial to achieve 100% SLO achievement if you just look at closed bugs. Even though there would be a major problem in the company, 99% of all bugs are overdue. As long as I only close ones that are still within the SLO, I'll have great achievement. So I think we shouldn't be looking at the closed bugs. 
                      I think we should be looking at open bugs, the entire population or percentage of those is within the SLO time. I think we're doing it the wrong way. Thanks for the feedback, Sid. Hence why we wanted to have the average age to measure what's outside in the open. We can make this iteration to measure also focus on the age of all opened, including open bugs. This is also something I have discussed with Christopher in the next iteration as well. And we're happy, more than happy to adjust. So the key... Yeah, go ahead. So average age would get closer to it. It's not what I'm proposing. What I'm proposing is of the open bugs or percentages outside of SLO. So display it as a percentage you do now, just do it about the open bugs, not the closed ones. Ah, got it. Okay. The exceeding SLO for open bugs. Yeah, or open bugs that are within SLO. So you have a chart that should go up and to the right, like everything else. Sounds great. We can take it to the next data metrics work stream to deliver this. Cool, thanks. It's a little tricky, Mac. You'll have to figure out how to... 
                      Because we like to be able to have charts that we can historically reconstruct if we need to. So when tickets close out, you need to go through their history to figure out at this time when it was open, did it breach the SLO or not? That's a good point. This might be much harder computationally. So I totally respect if we can't do it for that reason. Cool. Nine, Craig. Yeah, I just wanted to ask the team, I went through all the key meeting metrics, everything looked in line with prior periods and looked good. Is there anything the team wants to call out, especially that we should be watching? Yeah, I'll call out Sus. So the good news is in Q4, we had our smallest decline over several quarters. So we only went down by a tenth of a point. The quarter previous was 0.6 or six tenths of a point and the quarter before that was a full point. So we see this as an improvement, even though it was still a decline, but it's still a decline. Obviously, we want this actually tracking in upward direction. We also don't have enough data to know whether or not this is an actual real trend up. 
                      So I'm optimistic. I think this is a good thing. We have had a much keener focus on Sus over the past several quarters. So that's why I think, okay, the work that we've done, I think actually is catching up and getting noticed in Sus, but we got to keep an eye on it. We cannot assume that that's the case. Yeah, and the bug discussion above just kind of points out that we have an underlying problem right now in our metrics measurement. So if we change the measurements to reflect that,""")